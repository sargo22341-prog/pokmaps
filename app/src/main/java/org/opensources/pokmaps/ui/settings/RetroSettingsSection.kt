package org.opensources.pokmaps.ui.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R

@Composable
internal fun RetroSettingsRoute(viewModel: RetroViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    RetroSettingsSection(state, viewModel::onAction)
}

@Composable
internal fun RetroSettingsSection(state: RetroUiState, onAction: (RetroAction) -> Unit) {
    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(stringResource(R.string.retro_title), style = MaterialTheme.typography.titleSmall)
        Text(stringResource(R.string.retro_read_only), style = MaterialTheme.typography.bodyMedium)
        if (state.loading) {
            CircularProgressIndicator()
        } else {
            val username = state.progress.username
            if (username == null) {
                RetroCredentialsForm(state, onAction)
            } else {
                Text(stringResource(R.string.retro_account, username))
                Text(stringResource(R.string.retro_counts, state.earnedCount, state.hardcoreCount))
                Text(
                    stringResource(
                        if (state.progress.synchronizedAt ==
                            null
                        ) {
                            R.string.retro_never_synced
                        } else {
                            R.string.retro_cached
                        }
                    )
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(enabled = !state.busy, onClick = { onAction(RetroAction.Synchronize) }) {
                        Text(stringResource(R.string.retro_sync))
                    }
                    TextButton(onClick = { onAction(RetroAction.Disconnect) }) {
                        Text(stringResource(R.string.retro_disconnect))
                    }
                }
            }
        }
        if (state.busy) CircularProgressIndicator()
        if (state.failed) {
            Text(stringResource(R.string.retro_error), color = MaterialTheme.colorScheme.error)
            TextButton(onClick = { onAction(RetroAction.Retry) }) { Text(stringResource(R.string.guide_retry)) }
        }
    }
}

@Composable
private fun RetroCredentialsForm(state: RetroUiState, onAction: (RetroAction) -> Unit) {
    var username by remember(state.connectionRevision) { mutableStateOf("") }
    // Aucun rememberSaveable : la clé ne doit pas entrer dans le Bundle de restauration.
    var apiKey by remember(state.connectionRevision) { mutableStateOf("") }
    OutlinedTextField(
        value = username,
        onValueChange = { username = it.take(32) },
        singleLine = true,
        label = { Text(stringResource(R.string.retro_username)) },
        enabled = !state.busy,
        modifier = Modifier.fillMaxWidth()
    )
    OutlinedTextField(
        value = apiKey,
        onValueChange = { apiKey = it.take(32) },
        singleLine = true,
        label = { Text(stringResource(R.string.retro_key)) },
        enabled = !state.busy,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
        visualTransformation = PasswordVisualTransformation(),
        modifier = Modifier.fillMaxWidth()
    )
    Button(
        enabled = !state.busy && username.isNotBlank() && apiKey.length == 32,
        onClick = { onAction(RetroAction.Connect(username, apiKey)) }
    ) { Text(stringResource(R.string.retro_connect)) }
}
