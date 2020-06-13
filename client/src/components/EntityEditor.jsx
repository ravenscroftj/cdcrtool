import React from 'react';
import { connect } from 'react-redux';
import { Modal, ModalBody, Col, Row, FormGroup, Form, Button } from 'react-bootstrap';
import ModalHeader from 'react-bootstrap/ModalHeader';
import { updateEntityEditor, saveUpdatedEntity } from '../actions/entity';


class TaskView extends React.Component {
    constructor() {
        super();

        this.updateMentionEnd = this.updateMentionEnd.bind(this);
        this.updateMentionStart = this.updateMentionStart.bind(this);
        this.renderMentionEditorPreview = this.renderMentionEditorPreview.bind(this);
        this.submitUpdateEntity = this.submitUpdateEntity.bind(this);
    }

    updateMentionStart(e) {
        this.props.updateEntityEditor({ ...this.props.editorState, start: parseInt(e.target.value) });
    }

    updateMentionEnd(e) {
        this.props.updateEntityEditor({ ...this.props.editorState, end: parseInt(e.target.value) });
    }

    renderMentionEditorPreview() {
        const { start, end, fullText } = this.props.editorState;

        if (!fullText) {
            return (<span></span>)
        }

        const context = 20;

        const prefix = (start > context) ? "..." + fullText.substring(start - context, start) : fullText.substring(0, start);


        const suffix = ((end + context) < fullText.length) ? fullText.substring(end, end + context) + "..." : fullText.substring(end);

        const entValue = fullText.substring(start, end);

        return (
            <span>{prefix}<mark><b>{entValue}</b></mark>{suffix}</span>
        )
    }

    submitUpdateEntity(){
        this.props.saveUpdatedEntity(this.props.editorState);
        this.props.hideCallback();
    }

    render() {
        return (<Modal show={this.props.show} onHide={this.props.hideCallback}>
            <ModalHeader closeButton>
                Edit Entity
            </ModalHeader>
            <ModalBody>
                <FormGroup>
                    <Row>
                        <Col sm={6}>
                            {this.renderMentionEditorPreview()}
                        </Col>
                        <Col>
                            <Row>
                                <Form.Label>Start Character</Form.Label>
                                <Form.Control type="number"
                                    label="Starting Position"
                                    onChange={this.updateMentionStart}
                                    value={this.props.editorState.start} />
                            </Row>
                            <Row>
                                <Form.Label>End Character</Form.Label>
                                <Form.Control type="number"
                                    label="Ending Position"
                                    onChange={this.updateMentionEnd}
                                    value={this.props.editorState.end} />
                            </Row>
                        </Col>
                    </Row>


                </FormGroup>
            </ModalBody>
            <Modal.Footer>
                <Button variant="secondary" onClick={this.props.hideCallback}>Cancel</Button>
                <Button variant="primary" onClick={this.submitUpdateEntity}>Confirm</Button>
            </Modal.Footer>
        </Modal>)
    }
}



const mapStateToProps = function (state) {
    return {
        editorState: state.entity.editorState,
    }
};

const mapDispatchToProps = { updateEntityEditor, saveUpdatedEntity };

export default connect(mapStateToProps, mapDispatchToProps)(TaskView);