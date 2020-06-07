import React, {Component} from 'react';
import AuthenticatedPageContainer from '../components/AuthenticatedPageContainer';
import TaskView from '../components/TaskView';

class TaskPage extends Component {
    render(){
        return (
        <AuthenticatedPageContainer>
            <TaskView/>
        </AuthenticatedPageContainer>
        )
    }
}

export default TaskPage;