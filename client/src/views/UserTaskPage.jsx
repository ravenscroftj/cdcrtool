import React, {Component} from 'react';
import AuthenticatedPageContainer from '../components/AuthenticatedPageContainer';
import UserTaskList from '../components/UserTaskList';
import { connect } from 'react-redux';

class UserTaskPage extends Component {
    render(){
        return (
        <AuthenticatedPageContainer>
            <h1>View Tasks</h1>

            <UserTaskList>

            </UserTaskList>
        </AuthenticatedPageContainer>
        )
    }
}

const mapStateToProps = function(state){
    return {
        isFetchingTaskList: state.task.isFetchingTaskList,
        currentTaskListNavigation: state.task.currentTaskListNavigation,
        currentTaskList: state.task.currentTaskList
    }
};

const mapDispatchToProps = {};


export default connect(mapStateToProps, mapDispatchToProps)(UserTaskPage);