import React from 'react';

import moment from 'moment';
import { connect } from 'react-redux';

import {EntityNode, EntityTree} from '../util/enttree';

import { Container, Navbar, NavItem, NavDropdown, Form, Button, Alert, FormGroup, FormControl, Spinner, Row, Collapse, Dropdown, Col } from 'react-bootstrap'

import "./TaskView.css"

import { fetchTask, setTaskError, submitAnswer, reportBadTask } from '../actions/task';
import {updateEntityEditor} from '../actions/entity';

import { AlertHeading } from 'react-bootstrap/Alert';
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

        this.state = {
            answerButtonsDisabled: false,
            showBadExampleModal: false,
            mentionEditorShow: false,
            mentionEditorMention:{
                target: null,
                start: 0,
                end: 0,
            }
        }
    }

    componentDidMount() {
        this.props.fetchTask(this.props.taskHash);
    }

    componentDidUpdate(prevProps, prevState) {
        this.checkTaskUpdate();
    }

    checkTaskUpdate() {
        console.log(this.props.taskHash);
        

        const timeoutThreshold = (Date.now() - (300 * 1000));
        const { isFetchingTask, taskLastUpdated, currentTask, taskError, taskHash } = this.props;


        if ((!currentTask || (taskHash && taskHash !== currentTask.hash) || (taskLastUpdated < timeoutThreshold)) && !(isFetchingTask || taskError)) {
            console.log("Fetch task", taskHash)
            this.props.fetchTask(taskHash);
        }
    }

    clearTaskError() {
        this.props.setTaskError(null);
    }

    handleAnswerButton(answer) {
        this.props.submitAnswer(answer, this.props.currentTask);
    }

    renderQuestion() {
        const { currentTask } = this.props;

        const newsEntBits = currentTask.news_ent.split(";");
        const sciEntBits = currentTask.sci_ent.split(";");

        return (
            <h2>Are <b>{newsEntBits[0]}</b> and <b>{sciEntBits[0]}</b> mentions of the same thing?</h2>
        )
    }

    renderEntitiesDoc(fullText, ents, primaryEnt){
        const { currentTask } = this.props;

        const sortFunc = (a,b) => (parseInt(a.split(";")[1])-parseInt(b.split(";")[1]));
        
        const entities = ents.sort(sortFunc);
        const entTree = new EntityTree(fullText);

        for (const ent of entities) {
            const entBits = ent.split(";");
            entTree.insert(new EntityNode(entBits[1], entBits[2], entBits[0], ent==primaryEnt));
        }

        console.log(entTree);

        return (
            <p>
                {entTree.render()}
            </p>
        );
    }

    

    renderScienceSummary() {
        const { currentTask } = this.props;
        return this.renderEntitiesDoc(currentTask.sci_text, currentTask.sci_ents, currentTask.sci_ent);
    }

    renderNewsSummary(){
        const { currentTask } = this.props;
        return this.renderEntitiesDoc(currentTask.news_text, currentTask.news_ents, currentTask.news_ent);
    }

    showMentionEditor(target){
        
        const {currentTask}=this.props;
        const originalEntity = target === "news" ? currentTask.news_ent : currentTask.sci_ent;
        const entBits = originalEntity.split(";");
        const fullText = target === "news" ? currentTask.news_text : currentTask.sci_text;
        const docID = target === "news" ? currentTask.news_article_id : currentTask.sci_paper_id;

        this.props.updateEntityEditor({target, fullText, originalEntity, docID, start: parseInt(entBits[1]), end: parseInt(entBits[2])})
        
        this.setState({mentionEditorShow:true})

    }

    updateMentionStart(e) {
        this.setState({mentionEditorMention:{...this.state.mentionEditorMention, start: e.target.value}});
    }

    updateMentionEnd(e) {
        this.setState({mentionEditorMention:{...this.state.mentionEditorMention, end: e.target.value}});
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


                        {this.props.isSendingAnswer ? (
                            <Spinner animation="border" role="status">
                                <span className="sr-only">Submitting Answer...</span>
                            </Spinner>
                        ) : (
                                <div>
                                    <Row className="taskButtons">
                                        <Button onClick={() => { this.handleAnswerButton('yes') }}>Yes</Button>
                                        <Button onClick={() => { this.handleAnswerButton('no') }}>No</Button>
                                        <Button onClick={() => { this.setState({ showBadExampleModal: true }) }}>Bad Example</Button>

                                        <Dropdown>
                                            <Dropdown.Toggle>Change Entities</Dropdown.Toggle>
                                            <Dropdown.Menu>
                                                <Dropdown.Item as="button"
                                                onClick={()=>this.showMentionEditor("news")}>Mention 1</Dropdown.Item>
                                                <Dropdown.Item as="button" onClick={()=>this.showMentionEditor("science")}>Mention 2</Dropdown.Item>
                                            </Dropdown.Menu>
                                        </Dropdown>
                                    </Row>

                                    <EntityEditor show={this.state.mentionEditorShow} hideCallback={()=>this.setState({mentionEditorShow:false})}/>
                                </div>

                                
                            )}



                        <h3>
                            News Summary
                            <small class="text-muted"><a href={currentTask.news_url} target="_blank">[Full Text]</a></small>
                        </h3>
                        {this.renderNewsSummary()}

                        <h3> Science Summary
                        <small class="text-muted"><a href={"http://dx.doi.org/" + currentTask.sci_url} target="_blank">[Full Text]</a></small>
                        </h3>
                        {this.renderScienceSummary()}

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

const mapDispatchToProps = { fetchTask, setTaskError, submitAnswer, reportBadTask, updateEntityEditor };

export default connect(mapStateToProps, mapDispatchToProps)(TaskView);