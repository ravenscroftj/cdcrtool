import React from 'react';
import ReactDOM from 'react-dom';
import './index.css';
import App from './App';
import {Provider} from 'react-redux'
import thunk from 'redux-thunk';

import * as serviceWorker from './serviceWorker';
import { createStore, applyMiddleware } from 'redux';
import { persistStore, persistReducer } from 'redux-persist'
import storage from 'redux-persist/lib/storage' // defaults to localStorage for web
import { PersistGate } from 'redux-persist/integration/react'

import rootReducer from './reducers';

import {BrowserRouter as Router, Switch, Route} from 'react-router-dom';

import TaskPage from './views/TaskPage';

import 'bootstrap/dist/css/bootstrap.css';

import logger from 'redux-logger';
import UserTaskPage from './views/UserTaskPage';


const persistConfig = {
  key: 'cdcrapp',
  storage
}

const persistedReducer = persistReducer(persistConfig, rootReducer)

const store = createStore(persistedReducer, applyMiddleware(thunk, logger));
const persistor = persistStore(store);

ReactDOM.render(
  <React.StrictMode>
    <Provider store={store}>
      <PersistGate loading={null} persistor={persistor}>
      <Router>
        <Switch>
          <Route path="/tasks">
            <UserTaskPage/>
          </Route>
          <Route path="/">
            <TaskPage/>
          </Route>
        </Switch>
      </Router>
      </PersistGate>
    </Provider>
  </React.StrictMode>,
  document.getElementById('root')
);

// If you want your app to work offline and load faster, you can change
// unregister() to register() below. Note this comes with some pitfalls.
// Learn more about service workers: https://bit.ly/CRA-PWA
serviceWorker.unregister();
