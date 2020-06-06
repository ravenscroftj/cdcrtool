/**
 * Page container that has user authentication and forces anonymous users to log in
 */

import {connect} from 'react-redux';
import React from 'react';
import PageContainer from './PageContainer';
import LoginForm from './LoginForm'

class AuthenticatedPageContainer extends React.Component{

    render(){

        let {loggedIn} = this.props;

        let loginForm = (<LoginForm/>);

        return(
            <PageContainer>
                {loggedIn ? this.children : loginForm}
            </PageContainer>
        );
    }

};

const mapStateToProps = (state) =>(
    {
        loggedIn: state.auth.loggedIn
    }
);

export default connect(mapStateToProps)(AuthenticatedPageContainer);