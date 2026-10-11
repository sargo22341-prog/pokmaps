package org.opensources.pokmaps.ui.common

import androidx.compose.runtime.Composable
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.map.OfferCurrency

@Composable
internal fun offerPrice(amount: Int, currency: OfferCurrency): String = when (currency) {
    OfferCurrency.MONEY -> stringResource(R.string.map_offer_price, amount)
    OfferCurrency.COINS -> pluralStringResource(R.plurals.coins, amount, amount)
    OfferCurrency.BATTLE_POINTS -> pluralStringResource(R.plurals.map_offer_battle_points, amount, amount)
    OfferCurrency.ASHES -> pluralStringResource(R.plurals.map_offer_ashes, amount, amount)
}
