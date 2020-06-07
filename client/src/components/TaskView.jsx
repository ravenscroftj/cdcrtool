import React from 'react';

import {connect} from 'react-redux';

import {Container, Navbar, NavItem, NavDropdown, Form, Button, Alert, FormGroup, FormControl, Spinner} from 'react-bootstrap'

import "./TaskView.css"

import {fetchTask, setTaskError, submitAnswer, reportBadTask} from '../actions/task';
import { AlertHeading } from 'react-bootstrap/Alert';
import BadTaskModal from './BadTaskModal';


class TaskView extends React.Component {

    constructor(){
        super();
        this.clearTaskError = this.clearTaskError.bind(this);
        this.handleAnswerButton = this.handleAnswerButton.bind(this);

        this.state = {
            answerButtonsDisabled: false,
            showBadExampleModal: false
        }
    }

    componentDidMount(){
        this.checkTaskUpdate();
        if(!this.props.isFetchingTask){
            this.props.fetchTask();
        }
    }

    componentDidUpdate(prevProps, prevState) {
        this.checkTaskUpdate();
    }

    checkTaskUpdate(){
        const timeoutThreshold = (Date.now() - (300*1000) );
        const {isFetchingTask, taskLastUpdated,currentTask, taskError} = this.props;
        if (( !currentTask || (taskLastUpdated < timeoutThreshold) ) && !( isFetchingTask || taskError)) {
            console.log("Fetch task")
            this.props.fetchTask();
        }
    }

    clearTaskError(){
        this.props.setTaskError(null);
    }

    handleAnswerButton(answer){
        this.props.submitAnswer(answer, this.props.currentTask);
    }

    renderQuestion(){
        const {currentTask} = this.props;

        const newsEntBits = currentTask.news_ent.split(";");
        const sciEntBits = currentTask.sci_ent.split(";");

        return (
         <h2>Are <b>{newsEntBits[0]}</b> and <b>{sciEntBits[0]}</b> mentions of the same thing?</h2>
        )
    }

    renderNewsSummary(){
        const {currentTask} = this.props;
        const newsEntBits = currentTask.news_ent.split(";");

        const start = parseInt(newsEntBits[1]);
        const end = parseInt(newsEntBits[2]);       

        return (
            <p>
                {currentTask.news_text.substring(0, start)}
                <mark>
                {currentTask.news_text.substring(start, end)}  
                </mark>
                {currentTask.news_text.substring(end)}
            </p>
        );
    }

    renderScienceSummary(){
        const {currentTask} = this.props;
        const sciEntBits = currentTask.sci_ent.split(";");

        const start = parseInt(sciEntBits[1]);
        const end = parseInt(sciEntBits[2]);



        return (
            <p>
                {currentTask.sci_text.substring(0, start)}
                <mark>
                {currentTask.sci_text.substring(start, end)}  
                </mark>
                {currentTask.sci_text.substring(end)}
            </p>
        );
    }

    render(){
        const {currentTask, taskError, isFetchingTask} = this.props;

        let errorBlock = "";
        
        if (taskError){
            errorBlock = (
                <Alert variant="danger">
                <Alert.Heading>Oops...</Alert.Heading>
                Retrieving the task from the server failed: <b>{taskError.message}</b>

                <Button className="btn-danger" onClick={this.clearTaskError}>Retry</Button>
                </Alert>
            );
        }

        if(isFetchingTask){
            return (<Spinner animation="border" role="status">
                <span className="sr-only">Loading...</span>
            </Spinner>)
        }

        return(
            <div>
                { taskError ? errorBlock : (
                    <div>
                        {this.renderQuestion()}

                        
                            {this.props.isSendingAnswer ? (
                                <Spinner animation="border" role="status">
                                    <span className="sr-only">Submitting Answer...</span>
                                </Spinner>
                            ) : (
                                <div className="taskButtons">
                            <Button onClick={()=>{this.handleAnswerButton('yes')}}>Yes</Button>
                            <Button onClick={()=>{this.handleAnswerButton('no')}}>No</Button>
                            <Button onClick={()=>{this.setState({showBadExampleModal: true})}}>Bad Example</Button>
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
                            <FormControl type="text" readOnly={true} value={currentTask.hash}/>
                        </FormGroup>

                    </div>
                )}
                <BadTaskModal 
                show={this.state.showBadExampleModal} 
                submitCallback={(reason)=>{this.props.reportBadTask(currentTask, reason)}}
                hideCallback={()=>this.setState({showBadExampleModal:false})} />
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

const mapDispatchToProps = {fetchTask, setTaskError, submitAnswer, reportBadTask};

export default connect(mapStateToProps, mapDispatchToProps)(TaskView);