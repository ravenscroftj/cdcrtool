import React from 'react';
import moment from 'moment';
import { Modal, Form, Col, Row, Button, Accordion, Card, AccordionToggle, Spinner, Pagination } from 'react-bootstrap';
import { connect } from 'react-redux';

import {fetchUserTaskList, navigateTaskList} from '../actions/task';

class UserTaskList extends React.Component {

    constructor() {
        super();

    }

    componentDidMount(){
        this.props.fetchUserTaskList();

        this.movePage = this.movePage.bind(this);
    }

    movePage(pageNo) {
        const {currentTaskListNavigation} = this.props;

        let offset = pageNo * currentTaskListNavigation.limit;

        this.props.navigateTaskList(offset, currentTaskListNavigation.limit);
    }

    render() {

        const {currentTaskList, isFetchingTaskList, currentTaskListNavigation} = this.props;


        if (isFetchingTaskList || !currentTaskList) {
            return (<Spinner animation="border" role="status"><span className="sr-only">Loading...</span></Spinner>);
        }

        let buckets = {}

        for (const task of currentTaskList) {
            let bucket = moment(task.created_at).format("D/M/YYYY");

            if (!buckets.hasOwnProperty(bucket)){
                buckets[bucket] = [];
            }

            buckets[bucket].push(task);
            
        }

        const cards = Object.entries(buckets).map((bucket,idx) => (           
            <Card key={idx}>
                <Card.Header><AccordionToggle as={Button} variant="link" eventKey={idx}>{bucket[0]}</AccordionToggle></Card.Header>
                <Accordion.Collapse eventKey={idx}>
                <Card.Body>
                    <ul>
                        {bucket[1].map((item, linkIdx) => (
                        <li key={linkIdx}>
                            <b><a href={"/task/"+item.task.hash}>{moment(item.created_at).format("HH:mm:ss")}</a></b>
                        <mark>{item.task.news_ent.split(";")[0]}</mark> and <mark>{item.task.sci_ent.split(";")[0]}</mark> (<b>{item.answer}</b>)
                        </li>))}
                    </ul>
                </Card.Body>
                </Accordion.Collapse>
            </Card>
        ));

        const pages = Math.ceil(currentTaskListNavigation.total / currentTaskListNavigation.limit);
        const currentPage = currentTaskListNavigation.offset / currentTaskListNavigation.limit;

        let paginationPages = [];

        console.log("Current task nav:",currentTaskListNavigation);

        for(let i=0; i < pages; i++) {
            paginationPages.push(<Pagination.Item key={i} active={i===currentPage} onClick={() => this.movePage(i)}>{(i+1)}</Pagination.Item>);
        }

        return (
            <div>
            <Accordion defaultActiveKey={0}>
                {cards}
            </Accordion>
            <Row className="align-content-center">
            <Pagination>
            {paginationPages}
            </Pagination>
            </Row>
            </div>

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

const mapDispatchToProps = {fetchUserTaskList, navigateTaskList};


export default connect(mapStateToProps, mapDispatchToProps)(UserTaskList);