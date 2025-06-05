from ngapp.app import App
from ngapp.components import *


class MyVisComp(Div):
    def __init__(self):
        self.webgpu = WebgpuComponent()
        super().__init__(
            self.webgpu,
            ui_style="border: 1px solid #ccc; border-radius: 5px;",
            id="vis-comp",
        )
        self.on_load(self.__on_load)

    def __on_load(self):
        sol = self.storage.get("solution")
        if sol:
            self.draw(*sol)

    def draw(self, mesh, deformation, vonMises):
        import ngsolve_webgpu as nw

        self.storage.set("solution", (mesh, deformation, vonMises), use_pickle=True)

        self.meshdata = nw.MeshData(mesh)
        self.meshdata.deformation_data = nw.FunctionData(
            self.meshdata, deformation, order=5
        )
        vMdata = nw.FunctionData(self.meshdata, vonMises, order=5)
        colormap = nw.Colormap(colormap="viridis")
        renderer = nw.CFRenderer(vMdata, colormap=colormap)
        colorbar = nw.Colorbar(colormap)
        wireframe = nw.MeshWireframe2d(self.meshdata)
        self.webgpu.draw([wireframe, renderer, colorbar])


class BeamSolver(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        save_btn = QBtn(ui_icon="mdi-content-save", ui_flat=True).on_click(
            self.save_local
        )
        load_btn = QBtn(ui_icon="mdi-folder-open", ui_flat=True).on_click(
            self.load_local
        )
        toolbar = QToolbar(
            Heading("Beam Solver", 3),
            QSpace(),
            save_btn,
            load_btn,
            ui_class="bg-primary text-white",
        )
        self.set_colors(
            primary="#0D47A1",
            secondary="#90CAF9",
            accent="#FF9800",
            dark="#212121",
            positive="#2E7D32",
            negative="#C62828",
            info="#0288D1",
            warning="#F57C00",
        )

        self.button = QBtn(
            ui_color="positive",
            ui_icon="mdi-play",
            ui_flat=True,
            ui_round=True,
            ui_size="30px",
        )
        self.length = QInput(
            id="length",
            ui_model_value=5,
            ui_label="Length (m)",
            ui_style="width: 200px;",
        )
        self.width = QInput(
            id="width", ui_model_value=3, ui_label="Width (m)", ui_style="width: 200px;"
        )
        self.deform_slider = QSlider(
            ui_label=True,
            ui_model_value=1e5,
            ui_label_value="Deformation Scale: 1e5",
            ui_min=0,
            ui_max=1e5,
            ui_step=1e3,
            ui_style="width: 300px;",
        )
        self.deform_slider.on_update_model_value(self.update_deformation_slider)
        self.button.on("click", self.solve)
        self.vis_comp = MyVisComp()
        self.component = Div(
            toolbar,
            QCard(
                QCardSection(
                    Row(
                        Col(Centered(self.length, self.width)),
                        Col(Centered(self.button, self.deform_slider)),
                    )
                ),
                QCardSection(self.vis_comp),
                ui_flat=True,
            ),
        )
        self.component.on_load(self.update_deformation_slider)

    def update_deformation_slider(self):
        self.deform_slider.ui_label_value = (
            f"Deformation Scale: {self.deform_slider.ui_model_value:.1e}"
        )
        if hasattr(self.vis_comp, "meshdata"):
            self.vis_comp.meshdata.deformation_scale = self.deform_slider.ui_model_value
            self.vis_comp.webgpu.scene.render()

    def solve(self):
        import netgen.occ as ngocc
        import ngsolve as ngs

        length = float(self.length.ui_model_value)
        width = float(self.width.ui_model_value)
        r = ngocc.Rectangle(length, width).Face()
        r.edges.Min(ngocc.X).name = "left"
        r.edges.Max(ngocc.X).name = "right"
        maxh = 0.2 * min(length, width)
        geo = ngocc.OCCGeometry(r, dim=2)
        mesh = ngs.Mesh(geo.GenerateMesh(maxh=maxh))
        fes = ngs.VectorH1(mesh, order=3, dirichlet="left")
        u, v = fes.TnT()
        a = ngs.BilinearForm(fes)
        E = 210e9
        nu = 0.3
        mu = E / (2 * (1 + nu))
        lam = E * nu / ((1 + nu) * (1 - 2 * nu))
        strain = lambda u: ngs.Sym(ngs.Grad(u))
        stress = lambda s: lam * ngs.Trace(s) * ngs.Id(mesh.dim) + 2 * mu * s
        a += ngs.InnerProduct(stress(strain(u)), strain(v)) * ngs.dx
        a.Assemble()
        f = ngs.LinearForm(fes)
        surface = ngs.Integrate(ngs.CF(1), mesh.Boundaries("right"))
        force = ngs.CF((0, -1e5)) / surface
        f += force * v * ngs.ds("right")
        f.Assemble()
        u = ngs.GridFunction(fes)
        u.vec.data = a.mat.Inverse(fes.FreeDofs()) * f.vec

        deformation = ngs.CF((u[0], u[1], 0))
        vonMises = ngs.CF(
            ngs.sqrt(3 * ngs.InnerProduct(stress(strain(u)), stress(strain(u))))
        )
        self.vis_comp.draw(mesh, deformation, vonMises)
        self.vis_comp.meshdata.deformation_scale = self.deform_slider.ui_model_value
