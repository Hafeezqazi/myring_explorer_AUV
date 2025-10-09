"""
Interactive PyQt6 window hosting the myring profile explorer.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Optional

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSlider,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ..core import MyringParams, MyringResults, compute_myring_profile


class MainWindow(QMainWindow):
    """
    Interactive GUI for exploring the myring profile with live 2D/3D plots.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Myring Profile Explorer")

        self.params = MyringParams()
        self._pending_update = False
        self._last_results: Optional[MyringResults] = None

        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._perform_update)

        self._controls: Dict[str, QWidget] = {}
        self._metric_labels: Dict[str, QLabel] = {}
        self._optional_cache: Dict[str, Optional[float]] = {
            "r_front_desired": self.params.r_front_desired,
            "r_stern_desired": self.params.r_stern_desired,
        }
        self._scale_2d = {"x": 1.0, "y": 1.0}
        self._scale_3d = {"x": 1.0, "y": 1.0, "z": 1.0}
        self._scale_sliders: Dict[str, QSlider] = {}
        self._scale_labels: Dict[str, QLabel] = {}

        self._build_ui()
        self._perform_update()

    # -- UI construction -------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget(self)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(16)

        side_panel = self._build_side_panel()
        side_panel.setMaximumWidth(360)
        main_layout.addWidget(side_panel, stretch=0)

        plot_widget = self._build_plot_panel()
        main_layout.addWidget(plot_widget, stretch=1)

        self.setCentralWidget(central)
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)

    def _build_side_panel(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        form_box = QGroupBox("Geometry Inputs")
        form_layout = QFormLayout(form_box)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        for spec in self._parameter_specs():
            control = self._create_control(spec)
            form_layout.addRow(spec["label"], control)
            self._controls[spec["name"]] = control

        layout.addWidget(form_box)

        freeze_row = QHBoxLayout()
        freeze_row.setContentsMargins(0, 0, 0, 0)
        freeze_row.setSpacing(6)
        self.freeze_checkbox = QCheckBox("Freeze updates")
        self.freeze_checkbox.stateChanged.connect(self._on_freeze_toggled)
        freeze_row.addWidget(self.freeze_checkbox)

        apply_button = QPushButton("Apply Now")
        apply_button.clicked.connect(self._perform_update)
        freeze_row.addWidget(apply_button)
        layout.addLayout(freeze_row)

        reset_button = QPushButton("Reset Defaults")
        reset_button.clicked.connect(self._reset_defaults)
        layout.addWidget(reset_button)

        scale_box = self._create_scale_group()
        layout.addWidget(scale_box)

        metrics_box = self._create_metrics_group()
        layout.addWidget(metrics_box)
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_widget = QWidget()
        wrapper_layout = QVBoxLayout(scroll_widget)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(scroll)
        return scroll_widget

    def _build_plot_panel(self) -> QWidget:
        self.figure = Figure(figsize=(11.0, 6.4))
        self.figure.subplots_adjust(
            left=0.08, right=0.97, bottom=0.05, top=0.97, hspace=0.3
        )
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(640)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        self.ax_profile = self.figure.add_subplot(2, 1, 1)
        self.ax_surface = self.figure.add_subplot(2, 1, 2, projection="3d")

        plot_container = QWidget()
        plot_layout = QVBoxLayout(plot_container)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.setSpacing(0)
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas, stretch=1)
        return plot_container

    def _create_metrics_group(self) -> QGroupBox:
        metrics_box = QGroupBox("Calculated Metrics")
        metrics_layout = QFormLayout(metrics_box)
        metrics_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        for key, label in [
            ("length", "Effective Length L (m)"),
            ("L_over_D", "L/D Ratio"),
            ("volume", "Volume (m^3)"),
            ("cb_x", "CB_x (m)"),
            ("front_radius", "Front Radius (mm)"),
            ("stern_radius", "Stern Radius (mm)"),
            ("surface_area", "Wetted Surface (m^2)"),
            ("a_offset", "Head Offset Used (m)"),
            ("c_offset", "Tail Offset Used (m)"),
            ("Re_L", "Reynolds Re_L"),
            ("Cf", "Friction Coefficient C_f"),
            ("Df", "Friction Drag D_f (N)"),
        ]:
            value_label = QLabel("--")
            value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            metrics_layout.addRow(label + ":", value_label)
            self._metric_labels[key] = value_label

        return metrics_box

    def _create_scale_group(self) -> QGroupBox:
        group = QGroupBox("Plot Scaling")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        layout.addWidget(QLabel("2D Profile Axes"))
        for axis in ("x", "y"):
            layout.addLayout(self._make_scale_row(plot="2d", axis=axis))

        layout.addWidget(QLabel("3D Surface Axes"))
        for axis in ("x", "y", "z"):
            layout.addLayout(self._make_scale_row(plot="3d", axis=axis))

        return group

    def _make_scale_row(self, plot: str, axis: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        label = QLabel(f"{plot.upper()} {axis.upper()}:")
        row.addWidget(label)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(50, 200)
        slider.setValue(100)
        slider.setSingleStep(5)
        slider.setPageStep(10)
        slider.setTickPosition(QSlider.TickPosition.NoTicks)
        slider.valueChanged.connect(
            lambda value, plot=plot, axis=axis: self._on_scale_changed(plot, axis, value)
        )
        slider.setToolTip("Adjust axis scale (50% - 200%)")
        row.addWidget(slider, stretch=1)

        value_label = QLabel("1.00x")
        value_label.setMinimumWidth(48)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(value_label)

        key = f"{plot}_{axis}"
        self._scale_sliders[key] = slider
        self._scale_labels[key] = value_label

        return row

    # -- Parameter definitions -------------------------------------------
    @staticmethod
    def _parameter_specs() -> list[Dict[str, object]]:
        """
        Metadata describing each input control.
        """

        return [
            {"name": "d", "label": "Max Diameter d (m)", "type": "float", "min": 0.05, "max": 5.0, "step": 0.001, "decimals": 6},
            {"name": "n_head", "label": "Head Exponent n", "type": "float", "min": 0.1, "max": 10.0, "step": 0.1, "decimals": 3},
            {"name": "head_size", "label": "Full Head Length a (m)", "type": "float", "min": 0.05, "max": 1.5, "step": 0.001, "decimals": 6},
            {"name": "mid_size", "label": "Full Mid Length b (m)", "type": "float", "min": 0.05, "max": 6.0, "step": 0.001, "decimals": 6},
            {"name": "tail_size", "label": "Full Tail Length c (m)", "type": "float", "min": 0.05, "max": 3.0, "step": 0.001, "decimals": 6},
            {"name": "theta_deg", "label": "Tail Half-Angle (deg)", "type": "float", "min": 0.0, "max": 60.0, "step": 0.1, "decimals": 2},
            {"name": "a_offset", "label": "Head Offset a_offset (m)", "type": "float", "min": 0.0, "max": 0.5, "step": 0.001, "decimals": 6},
            {"name": "c_offset", "label": "Tail Offset c_offset (m)", "type": "float", "min": 0.0, "max": 0.5, "step": 0.001, "decimals": 6},
            {"name": "r_front_desired", "label": "Front Radius Target (mm)", "type": "optional_float"},
            {"name": "r_stern_desired", "label": "Stern Radius Target (mm)", "type": "optional_float"},
            {
                "name": "points_per_meter",
                "label": "Points per meter",
                "type": "int",
                "min": 50,
                "max": 8000,
                "step": 50,
            },
            {"name": "rho", "label": "Fluid Density rho (kg/m^3)", "type": "float", "min": 500.0, "max": 1500.0, "step": 1.0, "decimals": 3},
            {
                "name": "nu",
                "label": "Kinematic Viscosity nu (m^2/s)",
                "type": "float",
                "min": 1e-7,
                "max": 1e-4,
                "step": 1e-7,
                "decimals": 9,
            },
            {"name": "U", "label": "Speed U (m/s)", "type": "float", "min": 0.0, "max": 50.0, "step": 0.1, "decimals": 3},
        ]

    def _create_control(self, spec: Dict[str, object]) -> QWidget:
        """
        Build a spinbox configured per parameter specification.
        """

        name = spec["name"]
        value = getattr(self.params, name)
        control_type = spec.get("type", "float")

        if control_type == "int":
            control = QSpinBox()
            control.setRange(int(spec["min"]), int(spec["max"]))
            control.setSingleStep(int(spec["step"]))
            control.setValue(int(value))
            control.valueChanged.connect(lambda val, key=name: self._on_param_changed(key, int(val)))
        elif control_type == "optional_float":
            control = QLineEdit()
            control.setPlaceholderText("auto")
            control.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if value is not None:
                control.setText(f"{value * 1000.0:.3f}")
            control.editingFinished.connect(
                lambda key=name, widget=control: self._on_optional_changed(key, widget)
            )
        else:  # float
            control = QDoubleSpinBox()
            control.setDecimals(int(spec["decimals"]))
            control.setRange(float(spec["min"]), float(spec["max"]))
            control.setSingleStep(float(spec["step"]))
            control.setValue(float(value))
            control.valueChanged.connect(lambda val, key=name: self._on_param_changed(key, float(val)))

        control.setObjectName(f"control_{name}")
        control.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if hasattr(control, "setKeyboardTracking"):
            control.setKeyboardTracking(False)
        return control

    # -- Event handlers --------------------------------------------------
    def _on_param_changed(self, name: str, value: float | int) -> None:
        setattr(self.params, name, value)
        self._schedule_update()

    def _on_optional_changed(self, name: str, widget: QLineEdit) -> None:
        text = widget.text().strip()
        if not text:
            setattr(self.params, name, None)
            self._optional_cache[name] = None
            self._schedule_update()
            return

        try:
            value_mm = float(text)
        except ValueError:
            self.statusBar().showMessage(f"Invalid numeric value for {name!r}.")
            prev = self._optional_cache.get(name)
            widget.blockSignals(True)
            widget.setText("" if prev is None else f"{prev * 1000.0:.3f}")
            widget.blockSignals(False)
            return

        value_m = value_mm / 1000.0
        setattr(self.params, name, value_m)
        self._optional_cache[name] = value_m
        self._schedule_update()

    def _on_scale_changed(self, plot: str, axis: str, value: int) -> None:
        factor = max(value, 1) / 100.0
        if plot == "2d":
            self._scale_2d[axis] = factor
        else:
            self._scale_3d[axis] = factor

        key = f"{plot}_{axis}"
        display = self._scale_labels.get(key)
        if display is not None:
            display.setText(f"{factor:.2f}x")

        self._schedule_update()

    def _on_freeze_toggled(self, checked: int) -> None:
        if not checked and self._pending_update:
            self._update_timer.start(0)

    def _schedule_update(self) -> None:
        self._pending_update = True
        if self.freeze_checkbox.isChecked():
            if self._update_timer.isActive():
                self._update_timer.stop()
            return

        if not self._update_timer.isActive():
            self._update_timer.start(75)

    def _reset_defaults(self) -> None:
        self.params = MyringParams()
        for name, control in self._controls.items():
            value = getattr(self.params, name)
            if isinstance(control, QSpinBox):
                control.blockSignals(True)
                control.setValue(int(value))
                control.blockSignals(False)
            elif isinstance(control, QDoubleSpinBox):
                control.blockSignals(True)
                control.setValue(float(value))
                control.blockSignals(False)
            elif isinstance(control, QLineEdit):
                control.blockSignals(True)
                control.setText("" if value is None else f"{value * 1000.0:.3f}")
                control.blockSignals(False)
                self._optional_cache[name] = value

        self._scale_2d = {"x": 1.0, "y": 1.0}
        self._scale_3d = {"x": 1.0, "y": 1.0, "z": 1.0}
        for key, slider in self._scale_sliders.items():
            slider.blockSignals(True)
            slider.setValue(100)
            slider.blockSignals(False)
            label = self._scale_labels.get(key)
            if label is not None:
                label.setText("1.00x")

        self._pending_update = True
        if self.freeze_checkbox.isChecked():
            QMessageBox.information(
                self,
                "Updates Frozen",
                "Defaults restored. Unfreeze the plot or click 'Apply Now' to refresh the view.",
            )
        else:
            self._perform_update()

    # -- Rendering -------------------------------------------------------
    def _perform_update(self) -> None:
        try:
            results = compute_myring_profile(self.params)
        except ValueError as exc:
            self.statusBar().showMessage(str(exc))
            return

        self.statusBar().clearMessage()
        self._last_results = results

        self._render_profile(results)
        self._render_surface(results)
        self._update_metrics(results)
        self._sync_dependent_parameters(results)
        self._update_radius_controls(results)
        self.canvas.draw_idle()
        self._pending_update = False

    def _render_profile(self, results: MyringResults) -> None:
        ax = self.ax_profile
        ax.clear()

        x = results.x_values
        r = results.radii
        ax.fill_between(x, r, -r, color=(0.7, 0.78, 1.0), alpha=0.5)
        profile_line = ax.plot(x, r, color="navy", linewidth=2, label="Profile")[0]
        ax.plot(x, -r, color="navy", linewidth=2)

        a_eff, b_full, _, total_length = results.lengths
        head_mid_x = a_eff
        mid_tail_x = a_eff + b_full

        cb_point = ax.plot(
            results.cb[0], 0.0, marker="o", color="red", markersize=7, label="Center of Buoyancy"
        )[0]
        front_marker = ax.plot(
            0.0, 0.0, marker="s", color="black", markersize=6, label="Front Cut"
        )[0]
        stern_marker = ax.plot(
            total_length, 0.0, marker="^", color="black", markersize=6, label="Stern Cut"
        )[0]
        head_line = ax.axvline(
            head_mid_x, color="dimgray", linestyle="--", linewidth=1.2, label="Head/Mid Junction"
        )
        tail_line = ax.axvline(
            mid_tail_x, color="dimgray", linestyle=":", linewidth=1.2, label="Mid/Tail Junction"
        )

        ax.set_xlabel("Length (m)")
        ax.set_ylabel("Radius (m)")
        ax.set_title("Truncated Myring Profile")

        max_radius = float(np.max(r)) if r.size else 0.5
        if max_radius <= 0.0:
            max_radius = 0.1
        margin_x = max(total_length * 0.03, 0.02)
        base_x_min = -margin_x
        base_x_max = total_length + margin_x
        base_x_width = max(base_x_max - base_x_min, 0.05)
        scale_x = self._scale_2d["x"]
        center_x = (base_x_min + base_x_max) / 2.0
        half_width = base_x_width * scale_x / 2.0
        ax.set_xlim(center_x - half_width, center_x + half_width)

        base_y_limit = max(max_radius * 1.2 * self._scale_2d["y"], 0.01)
        ax.set_ylim(-base_y_limit, base_y_limit)
        ax.grid(True, which="both", linestyle=":", linewidth=0.6)
        legend2d = ax.legend(
            handles=[profile_line, cb_point, head_line, tail_line, front_marker, stern_marker],
            loc="center left",
            bbox_to_anchor=(-0.18, 0.5),
            frameon=True,
        )
        legend2d.set_draggable(True, use_blit=False, update="bbox")

        ax.text(
            results.cb[0],
            base_y_limit * 0.25,
            f"CB: {results.cb[0]:.3f} m",
            color="red",
            fontweight="bold",
        )
        ax.text(
            0.02 * total_length,
            base_y_limit * 0.92,
            f"L = {total_length:.3f} m   |   L/D = {results.L_over_D:.2f}",
            color="navy",
            fontweight="bold",
        )
        ax.text(
            0.02 * total_length,
            base_y_limit * 0.82,
            f"Front radius: {results.front_radius:.3f} m ({results.front_radius * 1000.0:.1f} mm)",
            color="black",
        )
        ax.text(
            0.02 * total_length,
            base_y_limit * 0.72,
            f"Stern radius: {results.stern_radius:.3f} m ({results.stern_radius * 1000.0:.1f} mm)",
            color="black",
        )
        ax.text(
            0.02 * total_length,
            base_y_limit * 0.62,
            f"Volume: {results.volume:.6f} m^3   |   CBx: {results.cb[0]:.4f} m",
            color="black",
        )
        ax.text(
            0.02 * total_length,
            base_y_limit * 0.52,
            f"Wetted surface: {results.surface_area:.4f} m^2",
            color="black",
        )

    def _render_surface(self, results: MyringResults) -> None:
        ax = self.ax_surface
        ax.clear()

        surf = ax.plot_surface(
            results.surface["x"],
            results.surface["y"],
            results.surface["z"],
            color=(0.7, 0.78, 1.0),
            edgecolor="none",
            alpha=0.95,
        )
        surf.set_label("Hull Surface")

        cb_handle = ax.scatter(
            results.cb[0], 0.0, 0.0, color="red", s=35, label="Center of Buoyancy"
        )

        theta_ring = np.linspace(0.0, 2.0 * np.pi, 120)
        a_eff, b_full, _, total_length = results.lengths
        head_mid_x = a_eff
        mid_tail_x = a_eff + b_full
        ring_points = [
            (0.0, "Front Cut", "#333333"),
            (head_mid_x, "Head/Mid Junction", "dimgray"),
            (mid_tail_x, "Mid/Tail Junction", "dimgray"),
            (total_length, "Stern Cut", "#111111"),
        ]

        ring_handles = []
        for x_pos, label, color in ring_points:
            radius = float(np.interp(x_pos, results.x_values, results.radii, left=np.nan, right=np.nan))
            if not np.isfinite(radius) or radius <= 0.0:
                continue
            y = radius * np.cos(theta_ring)
            z = radius * np.sin(theta_ring)
            line = ax.plot(np.full_like(theta_ring, x_pos), y, z, color=color, linewidth=2, label=label)[0]
            ring_handles.append(line)

        legend_handles = [surf, cb_handle, *ring_handles]
        legend3d = ax.legend(
            legend_handles,
            [h.get_label() for h in legend_handles],
            loc="center left",
            bbox_to_anchor=(-0.25, 0.5),
            frameon=True,
        )
        legend3d.set_draggable(True, use_blit=False, update="bbox")

        ax.set_xlabel("Length (m)")
        ax.set_ylabel("Width (m)")
        ax.set_zlabel("Height (m)")
        ax.set_title("3D Myring Profile")
        ax.view_init(elev=26, azim=-55)
        ax.dist = 5.0
        ax.set_anchor("C")

        length_min = float(results.x_values.min())
        length_max = float(results.x_values.max())
        length_range = length_max - length_min
        radius_range = float(np.max(results.radii)) if results.radii.size else 0.5
        if radius_range <= 0.0:
            radius_range = 0.5

        margin_x = max(length_range * 0.05, 0.02)
        margin_r = radius_range * 0.35

        base_x_min = length_min - margin_x
        base_x_max = length_max + margin_x
        base_x_range = max(base_x_max - base_x_min, 0.05)
        scale_x = self._scale_3d["x"]
        center_x = (base_x_min + base_x_max) / 2.0
        half_x = base_x_range * scale_x / 2.0
        x_min = center_x - half_x
        x_max = center_x + half_x

        base_y_limit = max((radius_range + margin_r) * self._scale_3d["y"], 0.01)
        base_z_limit = max((radius_range + margin_r) * self._scale_3d["z"], 0.01)

        ax.set_xlim(x_min, x_max)
        ax.set_ylim(-base_y_limit, base_y_limit)
        ax.set_zlim(-base_z_limit, base_z_limit)
        ax.set_box_aspect((x_max - x_min, 2.0 * base_y_limit, 2.0 * base_z_limit))

    def _update_metrics(self, results: MyringResults) -> None:
        length_total = results.lengths[3]
        self._metric_labels["length"].setText(f"{length_total:.4f}")
        self._metric_labels["L_over_D"].setText(f"{results.L_over_D:.3f}")
        self._metric_labels["volume"].setText(f"{results.volume:,.6f}")
        self._metric_labels["cb_x"].setText(f"{results.cb[0]:.5f}")
        self._metric_labels["front_radius"].setText(f"{results.front_radius * 1000.0:.1f}")
        self._metric_labels["stern_radius"].setText(f"{results.stern_radius * 1000.0:.1f}")
        self._metric_labels["surface_area"].setText(f"{results.surface_area:,.4f}")
        self._metric_labels["a_offset"].setText(f"{results.offsets[0]:.5f}")
        self._metric_labels["c_offset"].setText(f"{results.offsets[1]:.5f}")

        self._metric_labels["Re_L"].setText(
            f"{results.Re_L:,.2f}" if results.Re_L is not None else "--"
        )
        self._metric_labels["Cf"].setText(
            f"{results.Cf:.4g}" if results.Cf is not None else "--"
        )
        self._metric_labels["Df"].setText(
            f"{results.Df:,.3f}" if results.Df is not None else "--"
        )

    # -- Convenience -----------------------------------------------------
    def _sync_dependent_parameters(self, results: MyringResults) -> None:
        """
        When the user specifies target radii, propagate the resulting offsets
        back into the corresponding spin boxes so the coupled parameters stay
        aligned.
        """

        a_offset, c_offset = results.offsets

        if self.params.r_front_desired is not None:
            self.params.a_offset = a_offset
            control = self._controls.get("a_offset")
            if isinstance(control, QDoubleSpinBox):
                control.blockSignals(True)
                control.setValue(a_offset)
                control.blockSignals(False)

        if self.params.r_stern_desired is not None:
            self.params.c_offset = c_offset
            control = self._controls.get("c_offset")
            if isinstance(control, QDoubleSpinBox):
                control.blockSignals(True)
                control.setValue(c_offset)
                control.blockSignals(False)

    def _update_radius_controls(self, results: MyringResults) -> None:
        """
        Keep the radius input fields in sync with the current geometry, showing
        the actual cut radius in millimetres whether it is auto or user defined.
        """

        front_mm = results.front_radius * 1000.0
        stern_mm = results.stern_radius * 1000.0

        front_ctrl = self._controls.get("r_front_desired")
        if isinstance(front_ctrl, QLineEdit):
            front_ctrl.blockSignals(True)
            if self.params.r_front_desired is None:
                front_ctrl.setText("")
                front_ctrl.setPlaceholderText(f"{front_mm:.2f} (auto)")
            else:
                front_ctrl.setText(f"{front_mm:.3f}")
            front_ctrl.blockSignals(False)

        stern_ctrl = self._controls.get("r_stern_desired")
        if isinstance(stern_ctrl, QLineEdit):
            stern_ctrl.blockSignals(True)
            if self.params.r_stern_desired is None:
                stern_ctrl.setText("")
                stern_ctrl.setPlaceholderText(f"{stern_mm:.2f} (auto)")
            else:
                stern_ctrl.setText(f"{stern_mm:.3f}")
            stern_ctrl.blockSignals(False)

    def current_parameters(self) -> Dict[str, float]:
        """
        Expose current parameter set (useful for debugging/tests).
        """

        return asdict(self.params)
