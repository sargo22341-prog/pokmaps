package org.opensources.pokmaps.ui.about

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.BuildConfig
import org.opensources.pokmaps.R

/** Crédits des sources de données et mentions légales. */
@Composable
fun AboutScreen(modifier: Modifier = Modifier) {
    Column(
        modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(stringResource(R.string.app_name), style = MaterialTheme.typography.headlineMedium)
        Text(
            stringResource(R.string.about_version, BuildConfig.VERSION_NAME),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Text(stringResource(R.string.about_description), style = MaterialTheme.typography.bodyLarge)
        Text(stringResource(R.string.about_sources_title), style = MaterialTheme.typography.titleMedium)
        Credit(R.string.about_credit_pokeapi_title, R.string.about_credit_pokeapi)
        Credit(R.string.about_credit_pokesprite_title, R.string.about_credit_pokesprite)
        Credit(R.string.about_credit_sprites_title, R.string.about_credit_sprites)
        Credit(R.string.about_credit_pret_title, R.string.about_credit_pret)
        Credit(R.string.about_credit_meteocons_title, R.string.about_credit_meteocons)
        Text(stringResource(R.string.about_legal_title), style = MaterialTheme.typography.titleMedium)
        Text(stringResource(R.string.about_legal), style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun Credit(title: Int, text: Int) {
    Column {
        Text(stringResource(title), style = MaterialTheme.typography.titleSmall)
        Text(
            stringResource(text),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}
