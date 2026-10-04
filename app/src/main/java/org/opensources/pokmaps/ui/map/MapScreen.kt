package org.opensources.pokmaps.ui.map

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import ovh.plrapps.mapcompose.ui.MapUI

@Composable
fun MapScreen(modifier: Modifier = Modifier, viewModel: MapViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    Box(modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        val mapState = state.mapState
        if (mapState == null) {
            CircularProgressIndicator()
        } else {
            MapUI(Modifier.fillMaxSize(), state = mapState)
        }
    }
}
