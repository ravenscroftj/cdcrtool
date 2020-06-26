/**
 * Redux actions for logging in and out of CDCR
 */

import Axios from 'axios'
import ApiEndpoints from '../ApiConfig';

import {fetchCurrentUserProfile} from './user';

const toggleLoggingIn = (isLoggingIn) => ({type: "TOGGLE_LOGGING_IN", isLoggingIn});
const setUserCredentials = (token, userID) => ({type: "SET_USER_CREDENTIALS", token, userID});
const setLoginError = (error) => ({type: "SET_LOGIN_ERROR", error});
const setLoggedIn = (loggedIn) => ({type:"SET_LOGGED_IN", loggedIn});


const addAuthHeaders = (state, headers) => {

    if(typeof(headers) == 'underfined'){
        headers = {};
    }

    return{...headers, 
        "Authentication-Token": state.auth.token
    }
}

function login(username, password){

    return async (dispatch) => {

        dispatch(toggleLoggingIn(true));
        dispatch(setLoginError(null));
        dispatch(setLoggedIn(false));


        try{
            const response = await Axios.post(ApiEndpoints.login, {"email":username, "password":password});

            let {id, authentication_token} = response.data.response.user;

            dispatch(setUserCredentials(authentication_token, id));
            dispatch(setLoggedIn(true));

        }catch(err) {
            dispatch(setLoginError(err));
        }
    

        dispatch(toggleLoggingIn(false));
        dispatch(fetchCurrentUserProfile());

    };

}

function logout(){

    return async(dispatch) => {
        
        try{
            const response = await Axios.get(ApiEndpoints.logout);

            dispatch(setUserCredentials(null,null));
        }catch(err){
            dispatch(setLoginError(err));
        }

        dispatch(setLoggedIn(false));

        
    }
}

export {login, logout, addAuthHeaders};