package org.opensources.pokmaps.ui.map

import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.input.nestedscroll.NestedScrollConnection
import androidx.compose.ui.input.nestedscroll.NestedScrollSource
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Velocity
import androidx.compose.ui.unit.dp

/** Seul le déplacement restant après le défilement du contenu ferme la fiche. */
@Composable
internal fun Modifier.detailDismissGesture(onClose: () -> Unit): Modifier {
    val threshold = with(LocalDensity.current) { 64.dp.toPx() }
    val connection = remember(onClose, threshold) {
        object : NestedScrollConnection {
            private var distance = 0f

            override fun onPostScroll(consumed: Offset, available: Offset, source: NestedScrollSource): Offset {
                if (source != NestedScrollSource.UserInput) return Offset.Zero
                distance = (distance + available.y).coerceAtLeast(0f)
                if (distance >= threshold) {
                    distance = 0f
                    onClose()
                }
                return Offset.Zero
            }

            override suspend fun onPostFling(consumed: Velocity, available: Velocity): Velocity {
                distance = 0f
                return Velocity.Zero
            }
        }
    }
    return nestedScroll(connection)
}
