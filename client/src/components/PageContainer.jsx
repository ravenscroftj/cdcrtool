import React from 'react';

import {connect} from 'react-redux';

import {Container, Navbar, NavItem, NavDropdown, Form, Button} from 'react-bootstrap'

import {login, logout} from '../actions/auth';

import './PageContainer.css';

class PageContainer extends React.Component {

    constructor(){
        super();

        this.logout = this.logout.bind(this);
    }

    logout(evt){
        evt.preventDefault();
        this.props.logout();
    }

    render(){

        const loginBar = this.props.loggedIn ? (
            <Navbar.Collapse className="justify-content-end">
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
        loggedIn: state.auth.loggedIn
    }
};

const mapDispatchToProps = {login,logout};


export default connect(mapStateToProps, mapDispatchToProps)(PageContainer);