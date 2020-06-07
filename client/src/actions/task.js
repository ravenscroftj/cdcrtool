import Axios from 'axios'
import ApiEndpoints from '../ApiConfig';

import {addAuthHeaders, logout} from './auth';
import {fetchCurrentUserProfile} from './user';


const setFetchingTask = (isFetchingTask) => ({type:"IS_FETCHING_TASK", isFetchingTask});
const setSendingAnswer = (isSendingAnswer) => ({type:"IS_SENDING_ANSWER", isSendingAnswer});
const setCurrentTask = (task) => ({type: "SET_CURRENT_TASK", task});
const setTaskError = (error) => ({type: "SET_TASK_ERROR", error});

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

export {fetchTask, setTaskError, submitAnswer, reportBadTask};