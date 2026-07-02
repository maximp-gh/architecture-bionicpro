import React from 'react';
import { ReactKeycloakProvider } from '@react-keycloak/web';
import Keycloak, { KeycloakConfig } from 'keycloak-js';
import ReportPage from './components/ReportPage';

const keycloakConfig: KeycloakConfig = {
  url: process.env.REACT_APP_KEYCLOAK_URL,
  realm: process.env.REACT_APP_KEYCLOAK_REALM||"",
  clientId: process.env.REACT_APP_KEYCLOAK_CLIENT_ID||""
};

const keycloak = new Keycloak(keycloakConfig);

const initOptions = {
  //onLoad: 'check-sso',        // Проверяем существующую сессию
  flow: 'standard',           // Явно указываем Authorization Code Flow
  //pkceMethod: 'S256',         // Включаем PKCE для безопасности
  responseMode: 'query',      // 👈 ГЛАВНОЕ: параметры в строке запроса, а не в фрагменте
  redirectUri: 'http://localhost:3001/auth/callback'
  //redirectUri: `${window.location.origin}/auth/callback`  // Явно указываем redirect_uri
};

const App: React.FC = () => {
  return (
    <ReactKeycloakProvider authClient={keycloak} initOptions={initOptions} >
      <div className="App">
        <ReportPage />
      </div>
    </ReactKeycloakProvider>
  );
};

export default App;