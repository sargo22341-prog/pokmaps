package org.opensources.pokmaps.ui.common

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.sizeIn
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import org.opensources.pokmaps.R

// Éléments communs des fiches (objet, lieu, personnage) et de la recherche.

/** Titre de section d'une fiche, sous un séparateur. */
@Composable
fun SheetSection(title: String, modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    Column(modifier.padding(horizontal = 16.dp, vertical = 8.dp)) {
        HorizontalDivider(Modifier.padding(bottom = 12.dp))
        Text(title, style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(bottom = 8.dp))
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) { content() }
    }
}

/**
 * Ligne d'une fiche ou d'un résultat : image, titre, icônes (rôles d'un personnage), sous-titre, texte à droite, et
 * bouton « Voir sur la carte ». Toucher la ligne ouvre la fiche de l'élément (`onClick`). L'image garde au moins la
 * place d'une icône ; un sprite de Pokémon peut être plus grand.
 */
@Composable
fun SheetRow(
    title: String,
    modifier: Modifier = Modifier,
    subtitle: String? = null,
    trailing: String? = null,
    onClick: (() -> Unit)? = null,
    onShowOnMap: (() -> Unit)? = null,
    labels: (@Composable () -> Unit)? = null,
    content: (@Composable () -> Unit)? = null
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
        modifier = modifier
            .fillMaxWidth()
            .clickable(enabled = onClick != null) { onClick?.invoke() }
            .padding(vertical = 4.dp)
    ) {
        if (content != null) {
            Box(Modifier.sizeIn(minWidth = ROW_IMAGE_SIZE, minHeight = ROW_IMAGE_SIZE), Alignment.Center) { content() }
        }
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.bodyLarge, maxLines = 2, overflow = TextOverflow.Ellipsis)
            labels?.invoke()
            if (!subtitle.isNullOrEmpty()) {
                Text(
                    subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 3,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }
        trailing?.let { Text(it, style = MaterialTheme.typography.titleSmall) }
        if (onShowOnMap != null) {
            FilledTonalIconButton(onClick = onShowOnMap) {
                Icon(painterResource(R.drawable.ic_map), stringResource(R.string.show_on_map))
            }
        }
    }
}

/** Fiche en cours de chargement, ou introuvable dans le jeu choisi. */
@Composable
fun SheetPlaceholder(loading: Boolean, message: String, modifier: Modifier = Modifier, failed: Boolean = false) {
    Box(modifier.fillMaxSize().padding(32.dp), contentAlignment = Alignment.Center) {
        when {
            loading -> CircularProgressIndicator()
            failed -> Text(stringResource(R.string.data_load_error), textAlign = TextAlign.Center)
            else -> Text(message, textAlign = TextAlign.Center)
        }
    }
}

private val ROW_IMAGE_SIZE = 56.dp
