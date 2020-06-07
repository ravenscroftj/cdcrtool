import React from 'react';

import {connect} from 'react-redux';

import {Container, Navbar, NavItem, NavDropdown, Form, Button, Spinner} from 'react-bootstrap'

import {login, logout} from '../actions/auth';

import {fetchCurrentUserProfile} from '../actions/user';

import './PageContainer.css';

class PageContainer extends React.Component {

    constructor(){
        super();

        this.logout = this.logout.bind(this);
    }

    componentDidMount(){
        if(!this.props.isFetchingUserProfile && this.props.loggedIn){
            this.props.fetchCurrentUserProfile();
        }
    }

    componentDidUpdate(){
        if(!this.props.currentUser && !this.props.isFetchingUserProfile && this.props.loggedIn){
            this.props.fetchCurrentUserProfile();
        }
    }

    logout(evt){
        evt.preventDefault();
        this.props.logout();
    }

    render(){

        const {currentUser, isFetchingUserProfile} = this.props;

        const loginBar = this.props.loggedIn ? (
            <Navbar.Collapse className="justify-content-end">
                <Navbar.Text>
                { (isFetchingUserProfile || !currentUser) ? 
                (<Spinner animation="border" role="status"><span className="sr-only">Loading...</span></Spinner>) : 
                ( <span>Welcome <b>{currentUser.username}</b>. You have completed <b>{currentUser.total_annotations}</b> examples.</span>)}
                </Navbar.Text>
                <Form inline onSubmit={this.logout}>
                    <Button type="submit">Log Out</Button>
                </Form>
            </Navbar.Collapse>
        ) : "";

        return(<div className="pagecontainer">
            <Navbar bg="dark" variant="dark">
                <Navbar.Brand>CDCRApp</Navbar.Brand>
                {loginBar}
            </Navbar>
            <Container className="maincontainer">
            {this.props.children}
            </Container>
        </div>)
    }

}


const mapStateToProps = function(state){
    return {
        loggedIn: state.auth.loggedIn,
        isFetchingUserProfile: state.user.isFetchingUserProfile,
        currentUser: state.user.user
    }
};

const mapDispatchToProps = {login,logout,fetchCurrentUserProfile};


export default connect(mapStateToProps, mapDispatchToProps)(PageContainer);