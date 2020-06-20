import React from 'react';
import { connect } from 'react-redux';
import { Modal, ModalBody, Col, Row, FormGroup, Form, Button, Alert } from 'react-bootstrap';
import ModalHeader from 'react-bootstrap/ModalHeader';
import { updateEntityEditor, saveUpdatedEntity } from '../actions/entity';


// if editor colides with an existing entity other than the original value
const COLLISION_EXISTING = "COLLISION_EXISTING";
// if editor collides with the original value (usually means the user didn't do anything)
const COLLISION_ORIGINAL  = "COLLISION_ORIGINAL";
// if there is no collision
const COLLISION_NONE = "COLLISION_NONE";

class TaskView extends React.Component {
    constructor() {
        super();

        this.updateMentionEnd = this.updateMentionEnd.bind(this);
        this.updateMentionStart = this.updateMentionStart.bind(this);
        this.renderMentionEditorPreview = this.renderMentionEditorPreview.bind(this);
        this.submitUpdateEntity = this.submitUpdateEntity.bind(this);
        this.checkForCollision = this.checkForCollision.bind(this);
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

    checkForCollision(){
        const {start,end,fullText, existingEnts, originalEntity} = this.props.editorState;


        const entStr = `${fullText.substring(start,end)};${start};${end}`;

        if (entStr === originalEntity){
            return COLLISION_ORIGINAL;
        }

        const existing = new Set(existingEnts);
        return existing.has(entStr) ? COLLISION_EXISTING : COLLISION_NONE;
    }

    submitUpdateEntity(){
        this.props.saveUpdatedEntity(this.props.editorState);
        this.props.hideCallback();
    }

    render() {

        const collisionState = this.checkForCollision();

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
                {collisionState == COLLISION_EXISTING? (
                    <Alert variant="warning">
                        <p>You can't save this entity because another one with the same boundaries exists. Try using "Swap Question Entities" instead.</p>
                    </Alert>
                ) : ""}
                {collisionState == COLLISION_ORIGINAL? (
                    <Alert variant="primary">
                        <p>Move the entity boundaries and click 'Confirm' to save.</p>
                    </Alert>
                ) : ""}

            </ModalBody>
            <Modal.Footer>
                <Button variant="secondary" onClick={this.props.hideCallback}>Cancel</Button>
                <Button variant="primary" onClick={this.submitUpdateEntity} disabled={collisionState !== COLLISION_NONE}>Confirm</Button>
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