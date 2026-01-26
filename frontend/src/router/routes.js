const routes = [
  // Login route (public, no layout)
  {
    path: '/login',
    component: () => import('pages/LoginPage.vue'),
  },
  
  // Main layout with authentication
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: 'home' },
      { path: 'home', component: () => import('pages/IndexPage.vue') },
      { path: 'api-data', component: () => import('pages/ApiDataPage.vue') },
      { path: 'capacitor', component: () => import('pages/CapacitorPage.vue') },
      
      // Mantelzorger routes
      { 
        path: 'mantelzorger/dashboard', 
        component: () => import('pages/MantelzorgerDashboard.vue'),
        meta: { requiresAuth: true, role: 'mantelzorger' }
      },
      
      // Patient routes
      { 
        path: 'patient/dashboard', 
        component: () => import('pages/PatientDashboard.vue'),
        meta: { requiresAuth: true, role: 'patient' }
      },
    ],
  },

  // Always leave this as last one,
  // but you can also remove it
  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue'),
  },
]

export default routes

