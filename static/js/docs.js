/* Swagger usa la misma sesion JWT y token CSRF del panel privado. */
SwaggerUIBundle({url: '/api/schema/', dom_id: '#swagger-ui', deepLinking: true,
  persistAuthorization: false, withCredentials: true,
  requestInterceptor: request => {request.headers['X-CSRFToken'] = window.Pulso.csrf(); return request;},
  presets: [SwaggerUIBundle.presets.apis], layout: 'BaseLayout'});
