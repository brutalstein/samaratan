"""Replaceable Godot 4 engine adapter: deterministic source and optional Windows export."""
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
from .models import GamePlan


class EngineError(RuntimeError):
    pass


MAIN_SCENE = '''[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://main.gd" id="1"]

[node name="SamaratanWorld" type="Node3D"]
script = ExtResource("1")
'''

# Deliberately elementary visual placeholders. This is an executable narrative prototype,
# NOT photorealism or AI-generated cinematic animation.
MAIN_SCRIPT = r'''extends Node3D

var game_data: Dictionary = {}
var scene_by_id: Dictionary = {}
var current_scene: String = ""
var actor: CharacterBody3D
var title_label: Label
var body_label: Label
var choices_box: VBoxContainer

func _ready() -> void:
    var json_text: String = FileAccess.get_file_as_string("res://game_data.json")
    var parsed = JSON.parse_string(json_text)
    if typeof(parsed) != TYPE_DICTIONARY:
        push_error("Invalid game_data.json")
        return
    game_data = parsed
    for beat in game_data["scenes"]:
        scene_by_id[beat["id"]] = beat
    _create_environment()
    _create_player()
    _create_hud()
    _show_beat(game_data["start_scene"])

func _create_environment() -> void:
    var floor_mesh := MeshInstance3D.new()
    var plane := PlaneMesh.new()
    plane.size = Vector2(40, 40)
    floor_mesh.mesh = plane
    var mat := StandardMaterial3D.new()
    mat.albedo_color = Color(0.10, 0.14, 0.18)
    mat.metallic = 0.35
    mat.roughness = 0.28
    floor_mesh.material_override = mat
    add_child(floor_mesh)
    var floor_body := StaticBody3D.new()
    var floor_collision := CollisionShape3D.new()
    var shape := BoxShape3D.new()
    shape.size = Vector3(40, 0.2, 40)
    floor_collision.shape = shape
    floor_collision.position.y = -0.12
    floor_body.add_child(floor_collision)
    add_child(floor_body)
    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-42, 25, 0)
    sun.light_energy = 0.4
    add_child(sun)
    for n in range(12):
        var block := MeshInstance3D.new()
        var box := BoxMesh.new()
        box.size = Vector3(2.8, 2.5 + float(n % 4) * 1.5, 2.8)
        block.mesh = box
        var block_mat := StandardMaterial3D.new()
        block_mat.albedo_color = Color(0.16, 0.20, 0.25)
        block.material_override = block_mat
        block.position = Vector3(-16 + float(n % 6) * 6.0, box.size.y / 2.0, -12 + float(n / 6) * 19.0)
        add_child(block)

func _create_player() -> void:
    actor = CharacterBody3D.new()
    actor.position = Vector3(0, 1.2, 5)
    var collider := CollisionShape3D.new()
    var capsule := CapsuleShape3D.new()
    capsule.height = 2.0
    collider.shape = capsule
    actor.add_child(collider)
    var body := MeshInstance3D.new()
    body.mesh = CapsuleMesh.new()
    var material := StandardMaterial3D.new()
    material.albedo_color = Color(0.3, 0.7, 0.8)
    body.material_override = material
    actor.add_child(body)
    add_child(actor)
    var camera := Camera3D.new()
    camera.position = Vector3(0, 3.1, 6.8)
    camera.rotation_degrees.x = -15
    camera.current = true
    actor.add_child(camera)

func _physics_process(delta: float) -> void:
    if actor == null:
        return
    var direction := Vector3.ZERO
    if Input.is_key_pressed(KEY_W): direction.z -= 1.0
    if Input.is_key_pressed(KEY_S): direction.z += 1.0
    if Input.is_key_pressed(KEY_A): direction.x -= 1.0
    if Input.is_key_pressed(KEY_D): direction.x += 1.0
    direction = direction.normalized()
    actor.velocity.x = direction.x * 4.0
    actor.velocity.z = direction.z * 4.0
    actor.velocity.y -= 18.0 * delta
    actor.move_and_slide()

func _create_hud() -> void:
    var layer := CanvasLayer.new()
    add_child(layer)
    var outer := PanelContainer.new()
    outer.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
    outer.offset_top = -255
    outer.offset_bottom = 0
    layer.add_child(outer)
    var margin := MarginContainer.new()
    margin.add_theme_constant_override("margin_left", 24)
    margin.add_theme_constant_override("margin_right", 24)
    margin.add_theme_constant_override("margin_top", 16)
    outer.add_child(margin)
    var column := VBoxContainer.new()
    margin.add_child(column)
    title_label = Label.new()
    title_label.add_theme_font_size_override("font_size", 24)
    column.add_child(title_label)
    body_label = Label.new()
    body_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    body_label.custom_minimum_size.y = 64
    column.add_child(body_label)
    choices_box = VBoxContainer.new()
    column.add_child(choices_box)
    var instructions := Label.new()
    instructions.text = "WASD: move • Click to choose story direction • Escape: quit"
    column.add_child(instructions)

func _show_beat(beat_id: String) -> void:
    current_scene = beat_id
    var beat: Dictionary = scene_by_id[beat_id]
    title_label.text = beat["title"]
    body_label.text = beat["narration"]
    for child in choices_box.get_children():
        choices_box.remove_child(child)
        child.queue_free()
    for choice in beat["choices"]:
        var button := Button.new()
        button.text = choice["label"]
        var next_beat: String = choice["next_scene"]
        button.pressed.connect(func(): _show_beat(next_beat))
        choices_box.add_child(button)
    if beat["choices"].is_empty():
        var ending := Label.new()
        ending.text = "END OF DEMO • Story authored with Samaratan"
        choices_box.add_child(ending)

func _unhandled_key_input(event: InputEvent) -> void:
    if event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
        get_tree().quit()
'''

EXPORT_PRESET = '''[preset.0]
name="Windows Desktop"
platform="Windows Desktop"
runnable=true
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter="*.json"
exclude_filter=""
export_path=""
[preset.0.options]
binary_format/architecture="x86_64"
binary_format/embed_pck=true
texture_format/bptc=true
texture_format/s3tc=true
texture_format/etc2=false
'''


class GodotAdapter:
    id = "godot4"

    def generate(self, plan: GamePlan, directory: Path) -> Path:
        project = directory / "game"
        project.mkdir(parents=True, exist_ok=True)
        name = json.dumps(plan.title, ensure_ascii=False)
        (project / "project.godot").write_text(
            '; Generated by Samaratan Studio\nconfig_version=5\n\n[application]\nconfig/name=' + name +
            '\nrun/main_scene="res://main.tscn"\n\n[rendering]\nrenderer/rendering_method="gl_compatibility"\nrenderer/rendering_method.mobile="gl_compatibility"\n',
            encoding="utf-8",
        )
        (project / "main.tscn").write_text(MAIN_SCENE, encoding="utf-8")
        (project / "main.gd").write_text(MAIN_SCRIPT, encoding="utf-8")
        (project / "game_data.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")
        (project / "export_presets.cfg").write_text(EXPORT_PRESET, encoding="utf-8")
        return project

    def bundle(self, project: Path, destination: Path) -> Path:
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for item in sorted(project.rglob("*")):
                if item.is_file() and not item.is_symlink():
                    archive.write(item, arcname=f"samaratan-game/{item.relative_to(project).as_posix()}")
        return destination

    def export_windows(self, project: Path, destination: Path, binary: str, timeout: int = 300) -> Path:
        if not shutil.which(binary):
            raise EngineError("Godot 4 CLI missing. Source ZIP is available; Windows export requires Godot and export templates on the build machine.")
        for argv in (
            [binary, "--headless", "--path", str(project), "--editor", "--import", "--quit"],
            [binary, "--headless", "--path", str(project), "--export-release", "Windows Desktop", str(destination)],
        ):
            try:
                outcome = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise EngineError(f"Godot build runner unavailable: {type(exc).__name__}") from exc
            if outcome.returncode != 0:
                raise EngineError(f"Godot failed during {'import' if '--import' in argv else 'export'} (code {outcome.returncode}). Check local export templates.")
        if not destination.is_file() or destination.stat().st_size == 0:
            raise EngineError("Godot export command returned success without producing an executable")
        return destination
