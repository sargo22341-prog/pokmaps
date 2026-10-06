package org.opensources.pokmaps.ui.common

/**
 * Délai pendant lequel un ViewModel garde ses flux actifs après la disparition de l'écran (`WhileSubscribed`) :
 * une rotation ou un aller-retour rapide ne relance pas les lectures.
 */
const val STOP_TIMEOUT_MS = 5_000L
