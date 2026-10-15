package org.opensources.pokmaps.domain.model

/** Évite de répéter le libellé lorsque la note éditoriale contient déjà la provenance structurée. */
object ExternalEvent {
    fun mentioned(text: String?): Boolean = text?.contains("événement externe", ignoreCase = true) == true
}
