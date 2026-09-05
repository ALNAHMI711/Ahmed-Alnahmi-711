import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

i18n.use(initReactI18next).init({
  lng: 'ar',
  fallbackLng: 'ar',
  interpolation: { escapeValue: false },
  resources: {
    ar: { translation: { welcome: 'مرحباً', login: 'تسجيل الدخول' } }
  }
})

export default i18n
