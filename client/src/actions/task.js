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

const submitAnswer = (answer, task, secondaryEntities) => {
    return async(dispatch, getState) => {
        dispatch(setSendingAnswer(true));

        let toUpdate = [];

        const relatedTaskSet = new Set(task.related_answers);

        // calculate whether we need to batch update or not
        for(const relatedTask of relatedTaskSet.values()) {
            const {news_ent, sci_ent} = relatedTask;

            // skip the current task if it appears (e.g. if we're amending)
            if(task.news_ent === relatedTask.news_ent && task.sci_ent === relatedTask.sci_ent){
                continue;
            }
            
            if(task.news_ent === relatedTask.news_ent ){

                if(relatedTask.answer === "yes" && !secondaryEntities.science.has(sci_ent)) {
                    toUpdate.push({news_ent, sci_ent, answer:"no"});
                }

                if(relatedTask.answer === "no" && secondaryEntities.science.has(sci_ent)) {
                    toUpdate.push({news_ent, sci_ent, answer:"yes"});
                }

            }else if(task.sci_ent == relatedTask.sci_ent) {

                if(relatedTask.answer === "yes" && !secondaryEntities.news.has(news_ent)) {
                    toUpdate.push({news_ent, sci_ent, answer:"no"});
                }

                if(relatedTask.answer === "no" && secondaryEntities.news.has(news_ent)) {
                    toUpdate.push({news_ent, sci_ent, answer:"yes"});
                }
            }

        }

        for(const sci_ent of secondaryEntities.science) {
            for(const news_ent of secondaryEntities.news) {
                const relatedTask = {news_ent, sci_ent, answer:"yes"};

                if(!relatedTaskSet.has(relatedTask)){
                    toUpdate.push(relatedTask);
                }
            }
        }



        if(toUpdate.size > 0){
            console.log("Batch update")
            //batch update
            try{
                console.log(toUpdate.values());
                const response = await Axios.request({
                    method: 'post',
                    url: `${ApiEndpoints.answers}`,
                    headers: addAuthHeaders(getState()),
                    data: {"answers": toUpdate, "news_article_id": task.news_article_id, "sci_paper_id": task.sci_paper_id}
                })
    
                dispatch(fetchTask());
                dispatch(fetchCurrentUserProfile())
    
            }catch(error) {
                dispatch(setTaskError(error));
            }



        }else{
            //single update
            try{

                const response = await Axios.request({
                    method: task.current_user_answer ? 'patch' : 'post',
                    url: `${ApiEndpoints.task}/${task.id}/answers`,
                    headers: addAuthHeaders(getState()),
                    data: {"answer": answer}
                })
    
                dispatch(fetchTask());
                dispatch(fetchCurrentUserProfile())
    
            }catch(error) {
                dispatch(setTaskError(error));
            }
        }


        dispatch(setSendingAnswer(false));

    };
}


const fetchTask = (hash, news_id, science_id, news_ent, sci_ent)=> {

    return async(dispatch, getState) => {

        dispatch(setFetchingTask(true));

        const {auth} = getState();

        let params = {};

        if(hash){
            params = {hash};
        }else if(news_id) {
            params = {news_id, science_id, news_ent, sci_ent};
        }

 
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

            
            let {offset,limit,total, tasks} = response.data;
            dispatch(setCurrentTaskList(tasks));
            dispatch(setTaskListNavigation({offset,limit,total}));

        }
        catch(error){
            setTaskError(error);
        }
        

        dispatch(setFetchingTaskList(false));

    };

}
const navigateTaskList = (offset, limit) => {
    return async(dispatch) =>{

        dispatch(setTaskListNavigation({offset,limit}));
        dispatch(fetchUserTaskList());
    }
};

export {fetchTask, setTaskError, submitAnswer, reportBadTask, fetchUserTaskList, navigateTaskList};