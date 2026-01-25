import { defineBoot } from '#q-app/wrappers'
import axios from 'axios'

// Be careful when using SSR for cross-request state pollution
// due to creating a Singleton instance here;
// If any client changes this (global) instance, it might be a
// good idea to move this instance creation inside of the
// "export default () => {}" function below (which runs individually
// for each client)
var API_ENDPOINT = ''
if (process.env.NODE_ENV === 'development') {
  API_ENDPOINT = process.env.API_ENDPOINT_DEV
} else if (process.env.NODE_ENV === 'production') {
  API_ENDPOINT = process.env.API_ENDPOINT_PROD
}
console.log('API_ENDPOINT is set to:', API_ENDPOINT)
const api = axios.create({ baseURL: API_ENDPOINT })

export default defineBoot(({ app }) => {
  // for use inside Vue files (Options API) through this.$axios and this.$api

  app.config.globalProperties.$axios = axios
  // ^ ^ ^ this will allow you to use this.$axios (for Vue Options API form)
  //       so you won't necessarily have to import axios in each vue file

  app.config.globalProperties.$api = api
  // ^ ^ ^ this will allow you to use this.$api (for Vue Options API form)
  //       so you can easily perform requests against your app's API
})

export { api }
