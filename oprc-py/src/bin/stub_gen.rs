
#[cfg(feature = "stub-gen")]
fn main() -> pyo3_stub_gen::Result<()> {
    // env_logger::Builder::from_env(env_logger::Env::default().filter_or("RUST_LOG", "info")).init();
    let stub = oprc_py::stub_info()?;
    stub.generate()?;
    Ok(())
}

#[cfg(not(feature = "stub-gen"))]
fn main() {
    println!(
        "Stub generation is disabled for the 'stub_gen' binary. \
        To enable it, ensure the 'stub-gen' feature is active when compiling this binary, \
        and that the 'oprc_py' library is also compiled with the 'stub-gen' feature."
    );
}