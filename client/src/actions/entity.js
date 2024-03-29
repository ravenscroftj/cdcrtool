import Axios from 'axios'
import ApiEndpoints from '../ApiConfig';

import {addAuthHeaders} from './auth';
import {fetchTask} from './task';

const updateEntityEditor = (state)=>({type:'UPDATE_ENTITY_EDITOR_STATE', state});
const setEntityUpdating = (isSavingEntity)=>({type:'SET_ENTITY_IS_UPDATING', isSavingEntity});
const setEntityError = (error) => ({type: 'SET_ENTITY_ERROR', error});


const saveUpdatedEntity = (entityEditorState) => {
    return async(dispatch, getState) => {

        dispatch(setEntityUpdating(true));

        const taskHash  = getState().task.currentTask.hash;
        const {start,end,fullText,originalEntity,docID,target} = entityEditorState;
        const newEntity = `${fullText.substring(start,end)};${start};${end}`;

        try{
            const response = await Axios.patch(`${ApiEndpoints.entities}/${target}/${docID}`, {oldEntity:originalEntity, newEntity}, {headers:addAuthHeaders(getState())});
            dispatch(fetchTask(taskHash));
        }catch(error){

        }

        dispatch(setEntityUpdating(false));

    }
};

const getEntitiesForDocument = (docType, docID) => {
    return async(dispatch, getState) => {
        dispatch(setEntityUpdating(true));
        

        try{
            const response = await Axios.get(`${ApiEndpoints.entities}/${docType}/${docID}`, {headers:addAuthHeaders(getState())});

        }catch(error){

        }

        dispatch(setEntityUpdating(false));
    };
};

export {updateEntityEditor, saveUpdatedEntity, getEntitiesForDocument};