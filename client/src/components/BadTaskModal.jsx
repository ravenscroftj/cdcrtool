import React from 'react';
import { Modal, Form, Col, Row, Button } from 'react-bootstrap';

class BadTaskModal extends React.Component {

    constructor(){
        super();

        this.state = {
            reason: null,
            reasonText: null
        };

        this.updateReason = this.updateReason.bind(this);
        this.confirmBadTask = this.confirmBadTask.bind(this);
    }

    updateReason(evt){
        if(evt.target.checked){
            this.setState({reason: evt.target.value});
        }
    }

    confirmBadTask(){
        this.props.hideCallback();

        this.props.submitCallback(this.state.reason === "other" ? this.state.reasonText : this.state.reason);
        
    }

    render() {
        return (
            <Modal show={this.props.show} onHide={this.props.hideCallback}>
                    <Modal.Header closeButton>
                        Mark Bad Example
                    </Modal.Header>
                    <Modal.Body>
                        <p>Please say why this is a bad task</p>
                        <Form>
                            <Form.Group as={Row}>
                                <Col sm={9}>
                                    <Form.Check type="radio" 
                                    onChange={this.updateReason} 
                                    checked={this.state.reason=="unrelated"} 
                                    label="News and science articles unrelated" 
                                    name="badExampleReason"
                                    value="unrelated"/>
                                    <Form.Check type="radio" 
                                    onChange={this.updateReason} 
                                    label="Text is garbled or incomprehensible" 
                                    checked={this.state.reason=="garbled"}
                                    name="badExampleReason"
                                    value="garbled"/>
                                    <Row>
                                        <Col xs="auto">
                                            <Form.Check type="radio" 
                                            onChange={this.updateReason} 
                                            checked={this.state.reason=="other"}  
                                            name="badExampleReason"
                                            value="other" />
                                        </Col>
                                        <Col>
                                            <Form.Control 
                                            type="text" 
                                            disabled={this.state.reason!="other"} 
                                            onChange={(evt)=>this.setState({reasonText:evt.target.value})}
                                            placeholder="Other reason" 
                                            name="badExampleReasonText" />
                                        </Col>
                                    </Row>
                                </Col>
                            </Form.Group>
                        </Form>

                    </Modal.Body>
                    <Modal.Footer>
                        <Button variant="secondary" onClick={this.props.hideCallback}>Cancel</Button>
                        <Button variant="primary" onClick={this.confirmBadTask}>Confirm</Button>
                    </Modal.Footer>
            </Modal>
        )
    }

}

export default BadTaskModal;