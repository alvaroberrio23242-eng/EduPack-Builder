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

  // --- Objetivos específicos (mismo patrón que preguntas: lista dinámica) ---
  const contenedorEspecificos = document.getElementById("especificos-contenedor");
  const tplEspecifico = document.getElementById("tpl-especifico");
  const btnAgregarEspecifico = document.getElementById("btn-agregar-especifico");

  function agregarEspecifico() {
    const nodo = tplEspecifico.content.cloneNode(true);
    const bloque = nodo.querySelector(".especifico-block");
    bloque.querySelector(".remove-especifico").addEventListener("click", () => {
      // Siempre deja al menos un campo, para no perder el objetivo general de foco.
      if (contenedorEspecificos.children.length > 1) bloque.remove();
    });
    contenedorEspecificos.appendChild(bloque);
  }

  btnAgregarEspecifico.addEventListener("click", agregarEspecifico);
  agregarEspecifico();
  agregarEspecifico(); // arranca con 2 campos, ya que "específicos" suele ser plural
});
