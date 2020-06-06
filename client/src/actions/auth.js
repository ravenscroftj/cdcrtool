/**
 * Redux actions for logging in and out of CDCR
 */

import Axios from 'axios'
import ApiEndpoints from '../ApiConfig';

const toggleLoggingIn = (isLoggingIn) => ({type: "TOGGLE_LOGGING_IN", isLoggingIn});
const setUserCredentials = (token, userID) => ({type: "SET_USER_CREDENTIALS", token, userID});
const setLoginError = (error) => ({type: "SET_LOGIN_ERROR", error});
const setLoggedIn = (loggedIn) => ({type:"SET_LOGGED_IN", loggedIn});


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

    };

}

function logout(){

}

export {login, logout};