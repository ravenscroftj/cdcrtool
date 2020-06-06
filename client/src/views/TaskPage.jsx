import React, {Component} from 'react';
import AuthenticatedPageContainer from '../components/AuthenticatedPageContainer';

class TaskPage extends Component {
    render(){
        return (
        <AuthenticatedPageContainer>
            <div>Hello!</div>
        </AuthenticatedPageContainer>
        )
    }
}

export default TaskPage;