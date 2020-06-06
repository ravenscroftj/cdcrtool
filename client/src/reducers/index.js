import {combineReducers} from 'redux'

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

const cdcrReducer = combineReducers({'auth':authReducer});


export default cdcrReducer;