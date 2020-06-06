import React from 'react';

import {connect} from 'react-redux';

import {Container, Navbar, NavItem} from 'react-bootstrap'

import {login, logout} from '../actions/auth';

import './PageContainer.css';

class PageContainer extends React.Component {

    render(){
        return(<div className="pagecontainer">
            <Navbar bg="dark" variant="dark">
                <Navbar.Brand>CDCRApp</Navbar.Brand>
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