/**
 * Endpoint config for API calls
 */

 const apiRoot = "http://localhost:5000";

 const Endpoints = {
     login: `${apiRoot}/login`,
     task: `${apiRoot}/api/v1/task`,
     user: `${apiRoot}/api/v1/user`,
 };

 export default Endpoints;