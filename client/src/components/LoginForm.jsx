import React from 'react';
import {connect} from 'react-redux';
import { Form, FormGroup, Button, Alert } from 'react-bootstrap';
import './LoginForm.css';

import {login} from '../actions/auth'

class LoginForm extends React.Component{

    constructor(){
        super();

        this.state = {
            formControls:{
                email: {
                    value: '',
                    placeholder: 'test@example.com'
                },
                password:{
                    value:'',
                    placeholder:'secret'
                }
            }
        };

        this.changeHandler = this.changeHandler.bind(this);
        this.submitLogin = this.submitLogin.bind(this);
    }

    submitLogin = (evt) => {
        evt.preventDefault();
        console.log(this.state.formControls);
        this.props.login(this.state.formControls.email.value, this.state.formControls.password.value);
    };

    changeHandler = event => {
        const name = event.target.name;
        const value = event.target.value;
      
        this.setState({
            formControls: {
              ...this.state.formControls,
              [name]: {value}
            }
        }); 
    }

    renderError() {
        const {loginError} = this.props;

        if (loginError.response) {

            if (loginError.response.status == 500){
                return(<Alert varient="danger">Login server is giving an internal server error. Contact Admin.</Alert>)
            }

            if (loginError.response.data.response) {
                const errors = loginError.response.data.response.errors;
            
                return(
                    <div>
                    <Alert varient="danger">
                        <ul>
                {Object.keys(errors).map( (key, idx) => (
                   <li key={idx}>{errors[key][0]}</li>
                ))}
                        </ul>
                    </Alert>
                    </div>
                )
            }

        }
    }

    render(){
        
        const {loggingIn, loginError} = this.props;

    

        return (
            <div>
            <h1>Log in to CDCR App</h1>
            {loginError ? this.renderError() : ""}
            <Form onSubmit={this.submitLogin}>
                <FormGroup controlId="formEmail">
                    <Form.Label>Email Address</Form.Label>
                    <Form.Control type="email" 
                    disabled={this.loggingIn}
                    name="email"
                    value={this.state.formControls.email.value}
                    placeholder={this.state.formControls.email.placeholder}
                    onChange={this.changeHandler}/>
                </FormGroup>
                <FormGroup>
                    <Form.Label>Password</Form.Label>
                    <Form.Control 
                    disabled={this.loggingIn}
                    type="password"
                    name="password"
                    value={this.state.formControls.password.value}
                    placeholder={this.state.formControls.password.placeholder}
                    onChange={this.changeHandler}/>

                </FormGroup>
                <FormGroup>
                    <Button type="submit" disabled={this.loggingIn}>Log In</Button>
                </FormGroup>
            </Form>
            </div>
        )
    }
}

const mapStateToProps = (state) => ({
    loggingIn: state.auth.loggingIn,
    loginError: state.auth.error,
});

const mapDispatchToProps = (dispatch) => ({
    login: (username, password) => dispatch(login(username, password))
});

export default connect(mapStateToProps, mapDispatchToProps)(LoginForm);