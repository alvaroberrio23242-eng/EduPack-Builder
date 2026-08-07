document.addEventListener("DOMContentLoaded", () => {
  const contenedor = document.getElementById("preguntas-contenedor");
  const tpl = document.getElementById("tpl-pregunta");
  const btnAgregar = document.getElementById("btn-agregar-pregunta");

  function agregarPregunta() {
    const nodo = tpl.content.cloneNode(true);
    const bloque = nodo.querySelector(".pregunta-block");
    const hidden = bloque.querySelector(".opciones-hidden");
    const opciones = bloque.querySelectorAll(".opcion-input");

    function sync() {
      const valores = Array.from(opciones).map(o => o.value.trim()).filter(Boolean);
      hidden.value = valores.join("|");
    }
    opciones.forEach(o => o.addEventListener("input", sync));

    bloque.querySelector(".remove-pregunta").addEventListener("click", () => bloque.remove());
    contenedor.appendChild(bloque);
  }

  btnAgregar.addEventListener("click", agregarPregunta);
  agregarPregunta(); // arranca con una pregunta lista para llenar
});
