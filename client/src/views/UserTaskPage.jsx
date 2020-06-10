import React, {Component} from 'react';
import AuthenticatedPageContainer from '../components/AuthenticatedPageContainer';

class UserTaskPage extends Component {
    render(){
        return (
        <AuthenticatedPageContainer>
            <h1>View Tasks</h1>
        </AuthenticatedPageContainer>
        )
    }
}

export default UserTaskPage;