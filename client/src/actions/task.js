import Axios from 'axios'
import ApiEndpoints from '../ApiConfig';

import {addAuthHeaders, logout} from './auth';
import {fetchCurrentUserProfile} from './user';


const setFetchingTask = (isFetchingTask) => ({type:"IS_FETCHING_TASK", isFetchingTask});
const setFetchingTaskList = (isFetchingTaskList) => ({type:"IS_FETCHING_TASK_LIST", isFetchingTaskList});
const setSendingAnswer = (isSendingAnswer) => ({type:"IS_SENDING_ANSWER", isSendingAnswer});
const setCurrentTask = (task) => ({type: "SET_CURRENT_TASK", task});
const setCurrentTaskList = (taskList) => ({type: "SET_CURRENT_TASK_LIST", taskList});
const setTaskError = (error) => ({type: "SET_TASK_ERROR", error});

const setTaskListNavigation = (navigation) => ({type: "SET_TASKLIST_NAVIGATION", navigation});

const reportBadTask = (task, reason) => {
    return async(dispatch, getState) => {
        dispatch(setSendingAnswer(true));

        try{
            const response = await Axios.post(`${ApiEndpoints.task}`,
               {"task_id":task.id, "is_bad":true, "is_bad_reason": reason},
               {headers: addAuthHeaders(getState())});

            console.log(reason);

            dispatch(fetchTask());
            dispatch(fetchCurrentUserProfile());
        }catch(error) {
            dispatch(setTaskError(error));
        }

        dispatch(setSendingAnswer(false));
    };
}

const submitAnswer = (answer, task) => {
    return async(dispatch, getState) => {
        dispatch(setSendingAnswer(true));
        
        try{
            const response = await Axios.post(`${ApiEndpoints.task}/${task.id}/answers`, {"answer": answer}, {headers: addAuthHeaders(getState())} );

            dispatch(fetchTask());
            dispatch(fetchCurrentUserProfile())

        }catch(error) {
            dispatch(setTaskError(error));
        }

        dispatch(setSendingAnswer(false));

    };
}


const fetchTask = (hash)=> {

    return async(dispatch, getState) => {

        dispatch(setFetchingTask(true));

        const {auth} = getState();
        const params = typeof(hash) != 'undefined' ? {hash} : {};

 
        try{
            const response = await Axios.get(ApiEndpoints.task, {params:params, headers:addAuthHeaders(getState())} );


            dispatch(setCurrentTask(response.data));

        }catch(error) {

            if (error.response.status == 401){
                dispatch(logout());
            }
            dispatch(setTaskError(error));
            
        }

        dispatch(setFetchingTask(false));
        

    };

}

/**
 * List tasks that the current user has completed
 */
const fetchUserTaskList = () => {

    return async(dispatch, getState) => {

        dispatch(setFetchingTaskList(true));

        try{
            const params = getState().task.currentTaskListNavigation;
            let response = await Axios.get(ApiEndpoints.userTasks, {params:params, headers:addAuthHeaders(getState())});

            dispatch(setCurrentTaskList(response.data.tasks));

        }
        catch(error){
            setTaskError(error);
        }
        

        dispatch(setFetchingTaskList(false));

    };

}
const navigateTaskList = (offset, limit) => {
    return async(dispatch) =>{

        dispatch(setTaskListNavigation(offset,limit));
        dispatch(fetchUserTaskList());
    }
};

export {fetchTask, setTaskError, submitAnswer, reportBadTask, fetchUserTaskList, navigateTaskList};