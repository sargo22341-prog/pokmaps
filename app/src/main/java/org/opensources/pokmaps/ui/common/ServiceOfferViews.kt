package org.opensources.pokmaps.ui.common

import androidx.annotation.StringRes
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.CharacterRole
import org.opensources.pokmaps.domain.map.CharacterService
import org.opensources.pokmaps.domain.map.NpcOffer
import org.opensources.pokmaps.domain.map.OfferCurrency

@Composable
internal fun Services(services: List<NpcOffer.Service>, rowConditions: Boolean) {
    if (services.isEmpty()) return
    SectionTitle(stringResource(R.string.map_offer_services))
    services.forEach { offer ->
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            RoleIcon(offer.service.role, size = 24.dp)
            Text(
                stringResource(
                    if (offer.service == CharacterService.MOVE_TUTOR &&
                        (offer.currency != OfferCurrency.COINS || offer.price == null)
                    ) {
                        R.string.service_move_tutor_generic
                    } else {
                        offer.service.description
                    }
                ),
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.weight(1f)
            )
            offer.price?.let {
                val price = offerPrice(it, offer.currency)
                Text(price, style = MaterialTheme.typography.titleSmall)
            }
        }
        offer.requiredItem?.let {
            Text(stringResource(R.string.map_offer_required_item, it.name), style = MaterialTheme.typography.bodySmall)
        }
        OfferRowCondition(offer, rowConditions)
    }
}

private val CharacterService.role: CharacterRole
    get() = when (this) {
        CharacterService.DAYCARE_EGG -> CharacterRole.DAYCARE
        CharacterService.DAYCARE_WITHDRAWAL -> CharacterRole.DAYCARE
        CharacterService.MOVE_RELEARNER -> CharacterRole.MOVE_RELEARNER
        CharacterService.HEAL -> CharacterRole.HEAL
        CharacterService.CABLE_CLUB -> CharacterRole.CABLE_CLUB
        CharacterService.NAME_RATER -> CharacterRole.NAME_RATER
        CharacterService.DAYCARE -> CharacterRole.DAYCARE
        CharacterService.MOVE_DELETER -> CharacterRole.MOVE_DELETER
        CharacterService.GROOMING -> CharacterRole.GROOMING
        CharacterService.MOVE_TUTOR -> CharacterRole.MOVE_TUTOR
    }

@get:StringRes
private val CharacterService.description: Int
    get() = when (this) {
        CharacterService.DAYCARE_EGG -> R.string.service_daycare_egg
        CharacterService.DAYCARE_WITHDRAWAL -> R.string.service_daycare_withdrawal
        CharacterService.MOVE_RELEARNER -> R.string.service_move_relearner
        CharacterService.HEAL -> R.string.service_heal
        CharacterService.CABLE_CLUB -> R.string.service_cable_club
        CharacterService.NAME_RATER -> R.string.service_name_rater
        CharacterService.DAYCARE -> R.string.service_daycare
        CharacterService.MOVE_DELETER -> R.string.service_move_deleter
        CharacterService.GROOMING -> R.string.service_grooming
        CharacterService.MOVE_TUTOR -> R.string.service_move_tutor
    }
