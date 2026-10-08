package org.opensources.pokmaps.ui.common

import androidx.annotation.StringRes
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import java.util.Locale
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.NpcOffer
import org.opensources.pokmaps.domain.map.OfferCondition
import org.opensources.pokmaps.domain.map.Weekday
import org.opensources.pokmaps.domain.model.EncounterTime

/**
 * Ce qu'exige une offre : jours et moments sur une ligne (« Le lundi, le matin »), puis chaque étape du scénario
 * (« Après la libération de la Tour Radio »). Rien pour une offre toujours possible.
 */
@Composable
fun OfferConditionLines(condition: OfferCondition, modifier: Modifier = Modifier) {
    if (condition.isAlways) return
    val lines = listOfNotNull(scheduleText(condition)) + condition.story
    Column(modifier, verticalArrangement = Arrangement.spacedBy(2.dp)) {
        lines.forEach { line ->
            Text(line, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

/** Condition propre à une offre, sous sa ligne, quand ses conditions ne sont pas communes à tout le personnage. */
@Composable
fun OfferRowCondition(offer: NpcOffer, shown: Boolean) {
    if (shown) OfferConditionLines(offer.condition, Modifier.padding(start = CONDITION_INDENT))
}

/** Jours puis moments, avec une majuscule initiale ; `null` si l'offre ne dépend ni du jour ni du moment. */
@Composable
private fun scheduleText(condition: OfferCondition): String? {
    val days = enumeration(Weekday.entries.filter { it in condition.weekdays }.map { stringResource(it.label) })
    val times = enumeration(EncounterTime.entries.filter { it in condition.times }.map { stringResource(it.label) })
    val text = when {
        days != null && times != null -> stringResource(R.string.offer_when_list_next, days, times)
        else -> days ?: times
    }
    return text?.replaceFirstChar { it.titlecase(Locale.FRENCH) }
}

/** « le lundi, le mercredi et le samedi » ; `null` pour une liste vide. */
@Composable
private fun enumeration(items: List<String>): String? {
    if (items.isEmpty()) return null
    val head = items.dropLast(1).reduceOrNull { first, next ->
        stringResource(R.string.offer_when_list_next, first, next)
    }
    return head?.let { stringResource(R.string.offer_when_list_last, it, items.last()) } ?: items.last()
}

@get:StringRes
private val Weekday.label: Int
    get() = when (this) {
        Weekday.MONDAY -> R.string.offer_when_monday
        Weekday.TUESDAY -> R.string.offer_when_tuesday
        Weekday.WEDNESDAY -> R.string.offer_when_wednesday
        Weekday.THURSDAY -> R.string.offer_when_thursday
        Weekday.FRIDAY -> R.string.offer_when_friday
        Weekday.SATURDAY -> R.string.offer_when_saturday
        Weekday.SUNDAY -> R.string.offer_when_sunday
    }

@get:StringRes
private val EncounterTime.label: Int
    get() = when (this) {
        EncounterTime.MORNING -> R.string.offer_when_morning
        EncounterTime.DAY -> R.string.offer_when_day
        EncounterTime.NIGHT -> R.string.offer_when_night
    }

/** Retrait des conditions sous la ligne d'une offre : largeur de l'icône et de l'espace qui la suit. */
private val CONDITION_INDENT = 40.dp
