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
            await Axios.post(`${ApiEndpoints.task}`,
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


const reportDifficultTask = (task) => {
    return async(dispatch, getState) => {
        dispatch(setSendingAnswer(true));

        try {
            await Axios.post(`${ApiEndpoints.task}`,
               {"task_id":task.id, "is_difficult":true},
               {headers: addAuthHeaders(getState())});

            dispatch(fetchTask(task.hash));
            dispatch(fetchCurrentUserProfile());
        }catch(error) {
            dispatch(setTaskError(error));
        }

        dispatch(setSendingAnswer(false));
    };
}

const submitAnswer = (answer, task, secondaryEntities, getNextTask) => {
    return async(dispatch, getState) => {
        dispatch(setSendingAnswer(true));

        let toUpdate = [];

        const relatedTaskSet = new Set(task.related_answers);

        // first see if the current answer has any null entities indicating singletons
        const singleton = !task.news_ent || !task.sci_ent;

        // if we're not dealing with singleton then calculate whether we need to batch update or not
        if(!singleton) {
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
    
            const allScienceEnts = Array.from(secondaryEntities.science).concat([task.sci_ent]);
            const allNewsEnts = Array.from(secondaryEntities.news).concat([task.news_ent]);
    
            for(const sci_ent of allScienceEnts) {
                for(const news_ent of allNewsEnts) {
    
                    if(sci_ent == task.sci_ent && news_ent == task.news_ent){
                        continue;
                    }
    
                    const relatedTask = {news_ent, sci_ent, answer:"yes"};
    
                    console.log(relatedTask,relatedTaskSet.has(relatedTask));
    
                    if(!relatedTaskSet.has(relatedTask)){
                        toUpdate.push(relatedTask);
                    }
                }
            }
        }



        // if toUpdate > 0 then we need to make batch updates
        // the code that builds toUpdate is guarded by singleton check
        // therefore this will always be false if singleton is false
        if(toUpdate.length > 0){
            console.log("Batch task update")
            
            // append 'current task' to batch
            const {news_ent, sci_ent} = task;
            toUpdate.push({news_ent, sci_ent, answer});
            //batch update
            try{
                const response = await Axios.request({
                    method: 'post',
                    url: `${ApiEndpoints.answers}`,
                    headers: addAuthHeaders(getState()),
                    data: {"answers": toUpdate, "news_article_id": task.news_article_id, "sci_paper_id": task.sci_paper_id}
                })
    
                dispatch(fetchTask(getNextTask ? null : task.hash));
                dispatch(fetchCurrentUserProfile())
    
            }catch(error) {
                dispatch(setTaskError(error));
            }


        // if not singleton and nothing in toUpdate then we can do 
        // a single task update.
        }else if(!singleton) {
            console.log("Single task update")
            //single update
            try{

                await Axios.request({
                    method: task.current_user_answer ? 'patch' : 'post',
                    url: `${ApiEndpoints.task}/${task.id}/answers`,
                    headers: addAuthHeaders(getState()),
                    data: {"answer": answer}
                })
    
                dispatch(fetchTask(getNextTask ? null : task.hash));
                dispatch(fetchCurrentUserProfile())
    
            }catch(error) {
                dispatch(setTaskError(error));
            }

        // now we deal with singleton submissions
        }else {
            console.log("Singleton update")

            try{

                const {news_article_id, sci_paper_id, news_ent, sci_ent} = task;

                await Axios.request({
                    method: 'post',
                    url: `${ApiEndpoints.task}/singletons`,
                    headers: addAuthHeaders(getState()),
                    data: {news_article_id, sci_paper_id, news_ent,sci_ent}
                })
    
                dispatch(fetchTask(getNextTask ? null : task.hash));
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

            if (error.response && error.response.status == 401){
                dispatch(logout());
            }else{
                dispatch(setTaskError(error));
            }
            
            
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

export {fetchTask, setTaskError, submitAnswer, reportBadTask, reportDifficultTask, fetchUserTaskList, navigateTaskList};