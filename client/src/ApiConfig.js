/**
 * Endpoint config for API calls
 */


const apiRoot = (window.location.host == "localhost:3000") ? "http://localhost:5000" : `${window.location.protocol}//${window.location.host}`;

 const Endpoints = {
     login: `${apiRoot}/login`,
     logout: `${apiRoot}/logout`,
     task: `${apiRoot}/api/v1/task`,
     user: `${apiRoot}/api/v1/user`,
     userTasks: `${apiRoot}/api/v1/user/tasks`,
     entities: `${apiRoot}/api/v1/entities`,
     answers: `${apiRoot}/api/v1/answers`
 };

 export default Endpoints;