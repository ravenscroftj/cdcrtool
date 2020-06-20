import React from 'react';

import moment from 'moment';
import { connect } from 'react-redux';

import {EntityNode, EntityTree} from '../util/enttree';

import { Form, Button, Alert, FormGroup, FormControl, Spinner, Row,  Dropdown,  ButtonGroup, SplitButton } from 'react-bootstrap'

import "./TaskView.css"

import { fetchTask, setTaskError, submitAnswer, reportBadTask, reportDifficultTask } from '../actions/task';
import {updateEntityEditor} from '../actions/entity';

import BadTaskModal from './BadTaskModal';
import EntityEditor from './EntityEditor';

class TaskView extends React.Component {

    constructor() {
        super();
        this.clearTaskError = this.clearTaskError.bind(this);
        this.handleAnswerButton = this.handleAnswerButton.bind(this);
        this.showMentionEditor = this.showMentionEditor.bind(this);
        this.updateMentionEnd = this.updateMentionEnd.bind(this);
        this.updateMentionStart = this.updateMentionStart.bind(this);
        this.refreshTaskWithNewEntities = this.refreshTaskWithNewEntities.bind(this);
        this.resetTask = this.resetTask.bind(this);
        this.editPrimaryEnts = this.editPrimaryEnts.bind(this);
        this.editSecondaryEnts = this.editSecondaryEnts.bind(this);
        this.storeSecondaryEntities = this.storeSecondaryEntities.bind(this);

        this.state = {
            answerButtonsDisabled: false,
            showBadExampleModal: false,
            mentionEditorShow: false,
            showAllEntities: false,
            changePrimaryEnts: false,
            changeSecondaryEnts: false,
            dirtyTask: false,

            originalEntities:{
                science: "",
                news: "",
            },

            secondaryEntities: {
                science: new Set(),
                news: new Set()
            },

            mentionEditorMention:{
                target: null,
                start: 0,
                end: 0,
            }
        }
    }

    componentDidMount() {
        this.props.fetchTask(this.props.taskHash);
        this.initSecondaryHighlights();
    }

    componentDidUpdate(prevProps, prevState) {
        this.checkTaskUpdate();


        if( (!prevProps.currentTask && this.props.currentTask) || (this.props.currentTask && this.props.currentTask.id !== prevProps.currentTask.id ) ){
            this.setState({dirtyTask:false});
            this.initSecondaryHighlights();
        }
    }

    initSecondaryHighlights(){
        const {currentTask} = this.props;
        const secondaryEntities = {news: new Set(), science: new Set()};

        if(!currentTask){
            return;
        }

        for (const task of currentTask.related_answers) {

            if(task.answer === "no"){
                continue;
            }

            if (task.news_ent === currentTask.news_ent && task.sci_ent !== currentTask.sci_ent){
                secondaryEntities.science.add(task.sci_ent);
            }else if(task.sci_ent === currentTask.sci_ent && task.news_ent !== currentTask.news_ent) {
                secondaryEntities.news.add(task.news_ent);
            }
        }

        this.setState({secondaryEntities});
    }

    checkTaskUpdate() {

        const { isFetchingTask, currentTask, taskError, taskHash } = this.props;


        if ((!currentTask || (taskHash && taskHash !== currentTask.hash)) && !(isFetchingTask || taskError)) {
            this.props.fetchTask(taskHash);
        }
    }

    clearTaskError() {
        this.props.setTaskError(null);
    }

    handleAnswerButton(answer) {
        this.props.submitAnswer(answer, this.props.currentTask, this.state.secondaryEntities);
    }

    editSecondaryEnts(){
        this.setState({
            changeSecondaryEnts: true,
            showAllEntities:true, 
            originalEntities: {
                science:this.props.currentTask.sci_ent,
                news: this.props.currentTask.news_ent
            } 
        });
    }

    editPrimaryEnts(){
        this.setState({
            changePrimaryEnts: true,
            showAllEntities: true,
            originalEntities: {
                science:this.props.currentTask.sci_ent,
                news: this.props.currentTask.news_ent
            }
        });
    }


    resetTask(){

        this.props.currentTask.sci_ent = this.state.originalEntities.science;
        this.props.currentTask.news_ent = this.state.originalEntities.news;

        this.setState({changePrimaryEnts: false,
            changeSecondaryEnts: false, 
            showAllEntities:false
        });

        this.initSecondaryHighlights();
    }

    renderQuestion() {
        const { currentTask } = this.props;

        const newsEntBits = currentTask.news_ent.split(";");
        const sciEntBits = currentTask.sci_ent.split(";");

        return (
            <h2>Are <b>{newsEntBits[0]}</b> and <b>{sciEntBits[0]}</b> mentions of the same thing?</h2>
        )
    }

    renderEntitiesDoc(fullText, ents, primaryEnts, secondaryEnts, onClickCallback, secondaryClass){
        const { currentTask } = this.props;

        const sortFunc = (a,b) => (parseInt(a.split(";")[1])-parseInt(b.split(";")[1]));
        
        const entities = ents? ents.sort(sortFunc) : [];
        const entTree = new EntityTree(fullText);


        for (const ent of entities) {
            
            if(!this.state.showAllEntities && !(primaryEnts.has(ent) || secondaryEnts.has(ent))){
                continue;
            }
            const entBits = ent.split(";");
            entTree.insert(new EntityNode(entBits[1], entBits[2], entBits[0], primaryEnts.has(ent), secondaryEnts.has(ent), onClickCallback, secondaryClass));
        }


        return (
            <div>
                {entTree.render()}
            </div>
        );
    }

    

    renderSummary(docType) {
        const { currentTask } = this.props;
        let {secondaryEntities} = this.state;

        const callback = (ent) => {

            if(this.state.changePrimaryEnts){
                if(docType == 'news'){
                    this.props.currentTask.news_ent = ent;
                }
                else{
                    this.props.currentTask.sci_ent = ent;
                }
                
                this.setState({dirtyTask:true});


            }else if(this.state.changeSecondaryEnts) {


               
                if(secondaryEntities[docType].has(ent)){
                    secondaryEntities[docType].delete(ent);
                }else{
                    secondaryEntities[docType].add(ent);
                }

                this.setState({secondaryEntities})
            }
        };

        const primaryEntities = new Set();
        //primaryEntities.
        if (docType == 'news'){
            primaryEntities.add(currentTask.news_ent);
        }else{
            primaryEntities.add(currentTask.sci_ent);
        }
        

        if(this.state.changePrimaryEnts) {
            secondaryEntities = {news: new Set(), science: new Set()};

            for (const task of currentTask.related_answers) {
                secondaryEntities.news.add(task.news_ent);
                secondaryEntities.science.add(task.sci_ent);
            }

        }

        const fullText = (docType=='news')?currentTask.news_text:currentTask.sci_text;
        const allEnts = (docType=='news')?currentTask.news_ents:currentTask.sci_ents;
        
        const secondaryClass = this.state.changePrimaryEnts ? 'text-primary' : 'text-success';
        return this.renderEntitiesDoc(fullText, allEnts, primaryEntities, secondaryEntities[docType], callback, secondaryClass);
    }

    renderNewsSummary(){
        const { currentTask } = this.props;
        const {secondaryEntities} = this.state;

        const callback = (ent) => {

            if(this.state.changePrimaryEnts){
                this.props.currentTask.news_ent = ent;
                this.setState({dirtyTask:true});
            }
        };

        const primaryEntities = new Set();
        primaryEntities.add(currentTask.news_ent);
        const secondaryClass = this.state.changePrimaryEnts ? 'text-primary' : 'text-success';
        return this.renderEntitiesDoc(currentTask.news_text, currentTask.news_ents,  primaryEntities, secondaryEntities.news, callback, secondaryClass);
    }

    showMentionEditor(target){
        
        const {currentTask}=this.props;
        const originalEntity = target === "news" ? currentTask.news_ent : currentTask.sci_ent;
        const entBits = originalEntity.split(";");
        const fullText = target === "news" ? currentTask.news_text : currentTask.sci_text;
        const docID = target === "news" ? currentTask.news_article_id : currentTask.sci_paper_id;
        const existingEnts = target === "news" ? currentTask.news_ents : currentTask.sci_ents;

        this.props.updateEntityEditor({target, fullText, originalEntity, docID, existingEnts, start: parseInt(entBits[1]), end: parseInt(entBits[2])})
        
        this.setState({mentionEditorShow:true})

    }

    updateMentionStart(e) {
        this.setState({mentionEditorMention:{...this.state.mentionEditorMention, start: e.target.value}});
    }

    updateMentionEnd(e) {
        this.setState({mentionEditorMention:{...this.state.mentionEditorMention, end: e.target.value}});
    }


    refreshTaskWithNewEntities(){
        const {currentTask} = this.props;
        this.setState({changePrimaryEnts: false, showAllEntities:false});
        this.props.fetchTask(null, currentTask.news_article_id, currentTask.sci_paper_id, currentTask.news_ent, currentTask.sci_ent);
    }


    storeSecondaryEntities(){
        this.setState({changeSecondaryEnts: false, showAllEntities:false});
    }

    renderTaskControlBlock(){

        if(this.state.changePrimaryEnts) {
            return(<div>
                
                <ButtonGroup>
                    <Button variant="success" onClick={this.refreshTaskWithNewEntities}>Confirm</Button>
                    <Button variant="danger" onClick={this.resetTask}>Cancel</Button>
                </ButtonGroup>

                <p>Please select which entities you want to use instead and click confirm.</p>
                <p>Mentions highlighted <span className="text-primary">blue</span> have already been annotated by you on a previous occasion.</p>
            </div>)
        } else if (this.state.changeSecondaryEnts) {

            return(<div>
                

                <ButtonGroup>
                    <Button variant="success" onClick={this.storeSecondaryEntities}>Confirm</Button>
                    <Button variant="danger" onClick={this.resetTask}>Cancel</Button>
                </ButtonGroup>

                <p>Click other entities that also co-refer to these phrases and click confirm. Click a <span className="text-success">green</span> mention to de-select it.</p>
            </div>)


        } else if(this.props.isSendingAnswer) {
            return (
                <Spinner animation="border" role="status">
                    <span className="sr-only">Submitting Answer...</span>
                </Spinner>
            );
        }else{
            return (
                <div>
                    <Row className="taskButtons">

                        <ButtonGroup>
                         <Button onClick={() => { this.handleAnswerButton('yes') }}>Yes</Button>
                        </ButtonGroup>

                        <ButtonGroup>
                        <Button onClick={() => { this.handleAnswerButton('no') }}>No</Button>
                        </ButtonGroup>

                        <ButtonGroup>
                        <Button onClick={() => { this.setState({ showBadExampleModal: true }) }}>Bad Example</Button>
                        </ButtonGroup>

                        {!this.props.currentTask.is_difficult ? (
                            <ButtonGroup>
                            <Button onClick={()=>this.props.reportDifficultTask(this.props.currentTask)}>This task is hard to think about</Button>
                            </ButtonGroup>
                        ) : ""}
                        


                        <Dropdown>
                            <Dropdown.Toggle>Options</Dropdown.Toggle>
                            <Dropdown.Menu>
                                <Dropdown.Item as="button"
                                onClick={()=>this.showMentionEditor("news")}>Move/Resize News Mention</Dropdown.Item>
                                <Dropdown.Item as="button" onClick={()=>this.showMentionEditor("science")}>Move/Resize Science Mention</Dropdown.Item>
                                <Dropdown.Item as="button" onClick={this.editPrimaryEnts}>Swap Question Entities</Dropdown.Item>
                                <Dropdown.Item as="button" onClick={this.editSecondaryEnts}>Add/Remove co-referring entities</Dropdown.Item>
                            </Dropdown.Menu>
                        </Dropdown>
                    </Row>

                    <EntityEditor show={this.state.mentionEditorShow} hideCallback={()=>this.setState({mentionEditorShow:false})}/>

                    {this.props.currentTask.is_difficult ? (
                        <p>This task was marked as difficult to think about by <b>{this.props.currentTask.is_difficult_user}</b> on <b>{moment(this.props.currentTask.is_difficult_reported_at).format("LLL")}</b> </p>
                    ) : ""}

                    <p>Mentions shown highlighted in <span className="text-success">green</span> are mentions that you have previously annotated as coreferent to one of the two entities.</p>
                    <p>You can add or remove these secondary mentions using the Options menu.</p>
                </div>

                
            )
        }
    }

    render() {
        const { currentTask, taskError, isFetchingTask } = this.props;

        let errorBlock = "";

        if (taskError) {
            errorBlock = (
                <Alert variant="danger">
                    <Alert.Heading>Oops...</Alert.Heading>
                Retrieving the task from the server failed: <b>{taskError.message}</b>

                    <Button className="btn-danger" onClick={this.clearTaskError}>Retry</Button>
                </Alert>
            );
        }

        if (isFetchingTask || !currentTask) {
            return (<Spinner animation="border" role="status">
                <span className="sr-only">Loading...</span>
            </Spinner>)
        }

        const currentAnsBlock = (currentTask.current_user_answer) ? (
        <Alert variant="info">You are amending an answer. You previously answered <b>{currentTask.current_user_answer.answer}</b> to this {moment(currentTask.current_user_answer.created_at).fromNow()}</Alert>
        ) : "";



        return (
            <div>
                {taskError ? errorBlock : (
                    <div>

                        {currentAnsBlock}
                        {this.renderQuestion()}

                        {this.renderTaskControlBlock()}

                        <h3>
                            News Summary
                            <small className="text-muted"><a href={currentTask.news_url} target="_blank">[Full Text]</a></small>
                        </h3>
                        <div className="entTree">{this.renderSummary('news')}</div>

                        <h3> Science Summary
                        <small className="text-muted"><a href={"http://dx.doi.org/" + currentTask.sci_url} target="_blank">[Full Text]</a></small>
                        </h3>
                        <div className="entTree">{this.renderSummary('science')}</div>

                        <FormGroup>
                            <Form.Label>Task Hash</Form.Label>
                            <FormControl type="text" readOnly={true} value={currentTask.hash} />
                        </FormGroup>

                    </div>
                )}
                <BadTaskModal
                    show={this.state.showBadExampleModal}
                    submitCallback={(reason) => { this.props.reportBadTask(currentTask, reason) }}
                    hideCallback={() => this.setState({ showBadExampleModal: false })} />
            </div>
        );
    }

}

const mapStateToProps = (state) => ({
    isFetchingTask: state.task.isFetchingTask,
    isSendingAnswer: state.task.isSendingAnswer,
    currentTask: state.task.currentTask,
    taskLastUpdated: state.task.taskLastUpdated,
    taskError: state.task.error
});

const mapDispatchToProps = { fetchTask, setTaskError, submitAnswer, reportBadTask, updateEntityEditor, reportDifficultTask };

export default connect(mapStateToProps, mapDispatchToProps)(TaskView);