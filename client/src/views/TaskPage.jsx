import React, {Component} from 'react';
import AuthenticatedPageContainer from '../components/AuthenticatedPageContainer';
import TaskView from '../components/TaskView';

class TaskPage extends Component {

    state = {
        task: null
    }

    componentDidMount(){
        const {hash} = this.props.match.params;

        this.setState({hash});
    }

    render(){
        
        return (
        <AuthenticatedPageContainer>
            <TaskView taskHash={this.state.hash}/>
        </AuthenticatedPageContainer>
        )
    }
}

export default TaskPage;