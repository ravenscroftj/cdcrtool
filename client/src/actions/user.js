import Axios from 'axios'
import ApiEndpoints from '../ApiConfig';

import {addAuthHeaders} from './auth';

const setFetchingUserInfo = (isFetchingUserProfile) => ({type:"IS_FETCHING_USER_PROFILE", isFetchingUserProfile});
const setCurrentUserProfile = (user) => ({type: "SET_CURRENT_USER_PROFILE", user});

const fetchCurrentUserProfile = () => {

    return async(dispatch, getState) => {

        dispatch(setFetchingUserInfo(true));

        try{
            const response = await Axios.get(ApiEndpoints.user, {headers:addAuthHeaders(getState())});
            dispatch(setCurrentUserProfile(response.data));
        }catch(error){

        }

        dispatch(setFetchingUserInfo(false));

    };
};

export {fetchCurrentUserProfile, setCurrentUserProfile};