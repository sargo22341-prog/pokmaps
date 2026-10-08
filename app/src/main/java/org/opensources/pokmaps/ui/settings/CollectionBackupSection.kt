package org.opensources.pokmaps.ui.settings

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import org.opensources.pokmaps.R

@Composable
internal fun CollectionBackupRoute(viewModel: CollectionBackupViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val export = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")) {
        it?.let { address -> viewModel.export(address.toString()) }
    }
    val import = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) {
        it?.let { address -> viewModel.import(address.toString()) }
    }
    CollectionBackupSection(state, {
        export.launch("pokmaps-collection.json")
    }, { import.launch(arrayOf("application/json")) })
}

@Composable
internal fun CollectionBackupSection(state: BackupUiState, onExport: () -> Unit, onImport: () -> Unit) {
    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(stringResource(R.string.backup_title), style = MaterialTheme.typography.titleSmall)
        Text(stringResource(R.string.backup_description), style = MaterialTheme.typography.bodyMedium)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(enabled = state != BackupUiState.BUSY, onClick = onExport) {
                Text(stringResource(R.string.backup_export))
            }
            Button(enabled = state != BackupUiState.BUSY, onClick = onImport) {
                Text(stringResource(R.string.backup_import))
            }
        }
        val message = when (state) {
            BackupUiState.READY -> null
            BackupUiState.BUSY -> R.string.backup_busy
            BackupUiState.EXPORTED -> R.string.backup_exported
            BackupUiState.IMPORTED -> R.string.backup_imported
            BackupUiState.ERROR -> R.string.backup_error
        }
        message?.let {
            Text(
                stringResource(it),
                color = if (state == BackupUiState.ERROR) {
                    MaterialTheme.colorScheme.error
                } else {
                    MaterialTheme.colorScheme.onSurface
                }
            )
        }
    }
}
