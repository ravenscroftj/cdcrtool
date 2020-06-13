import {combineReducers} from 'redux'


const defaultUserState = {
    isFetchingUserProfile: false,
    user: null
};

const userReducer = function(state,action){
    if (typeof(state) == 'undefined'){
        return defaultUserState;
    }

    switch(action.type){
        case "IS_FETCHING_USER_PROFILE":
            return{...state, isFetchingUserProfile: action.isFetchingUserProfile};

        case "SET_CURRENT_USER_PROFILE":
            return {...state, user: action.user};
            
        default:
            return state;
    }
};

const defaultTaskState = {
    isFetchingTask: false,
    isFetchingTaskList: false,
    isSendingAnswer: false,
    currentTask: null,
    currentTaskList: [],
    currentTaskListNavigation:{offset:0, limit:200, total:0} ,
    error: null,
    taskLastUpdated: null
};

const taskReducer = function(state, action) {

    if (typeof(state) == 'undefined'){
        return defaultTaskState;
    }

    switch(action.type){

        case "IS_SENDING_ANSWER":
            return {...state, isSendingAnswer: action.isSendingAnswer};

        case "SET_CURRENT_TASK":
            return {...state, currentTask: action.task, taskLastUpdated: Date.now()};

        case "SET_CURRENT_TASK_LIST":
            return {...state, currentTaskList: action.taskList};

        case "IS_FETCHING_TASK":
            return {...state, isFetchingTask: action.isFetchingTask};

        case "IS_FETCHING_TASK_LIST":
            return {...state, isFetchingTaskList: action.isFetchingTaskList};

        case "SET_TASK_ERROR":
            return {...state, error: action.error}

        case "SET_TASKLIST_NAVIGATION":
            return {...state, currentTaskListNavigation: action.navigation};

        default:
            return state;
    }

}


const defaultAuthState = {
    isLoggingIn: false,
    loggedIn: false,
    userID: null,
    token: null,
    error: null
}

const authReducer = function(state, action){

    if (typeof(state) == 'undefined'){
        return defaultAuthState;
    }

    switch(action.type){

        case "SET_USER_CREDENTIALS":
            return{...state, token: action.token, userID: action.userID};
        case "TOGGLE_LOGGING_IN":
            return {...state, isLoggingIn: action.isLoggingIn};

        case "SET_LOGIN_ERROR":
            return{...state, error: action.error};

        case "SET_LOGGED_IN":
            return {...state, loggedIn: action.loggedIn}

        default:
            return state;
    }
};

const defaultEntityState = {
    editorState: {start:null, end:null, target:null, fullText:null, originalEntity:null, docID: null},
    isSavingEntity: false,
    entityError: null,
    docEntities:{ newsDoc: [], sciDoc: [] }
};

const entityReducer = (state, action)=>{

    if (typeof(state) == 'undefined'){
        return defaultEntityState;
    }

    switch(action.type){
        case 'SET_IS_GETTING_ENTITIES':
            return {...state, }
        case 'UPDATE_ENTITY_EDITOR_STATE':
            return {...state, editorState: action.state};
        case 'SET_ENTITY_IS_UPDATING':
            return {...state, isSavingEntity: action.isSavingEntity};
        case 'SET_ENTITY_ERROR':
            return {...state, entityError: action.error};
        default:
            return state;
    }
};

const cdcrReducer = combineReducers({'auth':authReducer, 'task':taskReducer, 'user':userReducer, 'entity': entityReducer});


export default cdcrReducer;