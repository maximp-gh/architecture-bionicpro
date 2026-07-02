import React from 'react';
import { ReactKeycloakProvider } from '@react-keycloak/web';
import Keycloak, { KeycloakConfig } from 'keycloak-js';
import ReportPage from './components/ReportPage';

const keycloakConfig: KeycloakConfig = {
  url: process.env.REACT_APP_KEYCLOAK_URL,
  realm: process.env.REACT_APP_KEYCLOAK_REALM||"",
  clientId: process.env.REACT_APP_KEYCLOAK_CLIENT_ID||""
};

const initOptions = {
  onLoad: 'check-sso',        // Проверяет существующую SSO-сессию
  pkceMethod: 'S256',         // Включает PKCE с SHA-256
  flow: 'standard',           // Authorization Code Flow
  checkLoginIframe: true,     // Разрешает тихое обновление токенов
  enableLogging: true         // Логирование для отладки (опционально)
};

const keycloak = new Keycloak(keycloakConfig);

const App: React.FC = () => {
  return (
    <ReactKeycloakProvider
        authClient={keycloak}
        initOptions={initOptions}
    >
      <div className="App">
        <ReportPage />
      </div>
    </ReactKeycloakProvider>
  );
};

export default App;