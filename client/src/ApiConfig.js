/**
 * Endpoint config for API calls
 */


const apiRoot = (window.location.host == "localhost:3000") ? "http://localhost:5000" : `${window.location.protocol}//${window.location.host}`;

 const Endpoints = {
     login: `${apiRoot}/login`,
     task: `${apiRoot}/api/v1/task`,
     user: `${apiRoot}/api/v1/user`,
     entities: `${apiRoot}/api/v1/entities`,
 };

 export default Endpoints;