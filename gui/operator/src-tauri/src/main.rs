#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde_json::Value;
use std::path::PathBuf;
use std::process::Command;

fn repo_root() -> PathBuf {
    if let Ok(r) = std::env::var("PFY_ROOT") {
        return PathBuf::from(r);
    }
    if let Ok(exe) = std::env::current_exe() {
        let mut p = exe;
        for _ in 0..12 {
            match p.parent() {
                Some(parent) => {
                    p = parent.to_path_buf();
                    if p.join("scripts").join("pfy").exists() {
                        return p;
                    }
                }
                None => break,
            }
        }
    }
    std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

fn run_board(args: &[&str]) -> Result<Value, String> {
    let root = repo_root();
    let board = root.join("scripts").join("pfy-board.py");
    if !board.exists() {
        return Err(format!("missing {}", board.display()));
    }
    let out = Command::new("python3")
        .arg(&board)
        .args(args)
        .current_dir(&root)
        .output()
        .map_err(|e| e.to_string())?;
    let stdout = String::from_utf8_lossy(&out.stdout);
    match serde_json::from_str::<Value>(stdout.trim()) {
        Ok(v) => Ok(v),
        Err(e) => {
            let stderr = String::from_utf8_lossy(&out.stderr);
            Err(format!("board json: {e}; stdout={stdout}; stderr={stderr}"))
        }
    }
}

#[tauri::command]
fn snapshot() -> Result<Value, String> {
    run_board(&["--snapshot"])
}

#[tauri::command]
fn start_sidecar(id: String) -> Result<Value, String> {
    run_board(&["--start", &id])
}

#[tauri::command]
fn run_stage() -> Result<Value, String> {
    run_board(&["--stage"])
}

#[tauri::command]
fn launch_env() -> Result<Value, String> {
    run_board(&["--env"])
}

#[tauri::command]
fn pull_model(name: String) -> Result<Value, String> {
    run_board(&["--pull", &name])
}

#[tauri::command]
fn test_model() -> Result<Value, String> {
    run_board(&["--eval"])
}

#[tauri::command]
fn set_tool(id: String, on: bool) -> Result<Value, String> {
    let flag = if on { "on" } else { "off" };
    run_board(&["--tool", &id, flag])
}

#[tauri::command]
fn space_invaders() -> Result<Value, String> {
    run_board(&["--space-invaders"])
}

#[tauri::command]
fn lanes() -> Result<Value, String> {
    run_board(&["--lanes"])
}

#[tauri::command]
fn lane_detail(trace: String, lane: String) -> Result<Value, String> {
    run_board(&["--lane-detail", &trace, &lane])
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![snapshot, start_sidecar, run_stage, launch_env, pull_model, test_model, set_tool, space_invaders, lanes, lane_detail])
        .run(tauri::generate_context!())
        .expect("error while running pfy-operator");
}
