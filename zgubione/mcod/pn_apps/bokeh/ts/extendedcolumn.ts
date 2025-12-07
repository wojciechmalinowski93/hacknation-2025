import { Box, BoxView } from "models/layouts/box"
import { Column as ColumnLayout, RowsSizing } from "core/layout/grid"
import * as p from "core/properties"

export class ExtendedColumnView extends BoxView {
    model: ExtendedColumn

    render(): void {
        super.render()
        this.el.setAttribute('aria-hidden', this.model.aria_hidden.toString())
    }

    _update_layout(): void {
        const items = this.child_views.map((child) => child.layout)
        this.layout = new ColumnLayout(items)
        this.layout.rows = this.model.rows
        this.layout.spacing = [this.model.spacing, 0]
        this.layout.set_sizing(this.box_sizing())
    }
}

export namespace ExtendedColumn {
    export type Attrs = p.AttrsOf<Props>

    export type Props = Box.Props & {
        rows: p.Property<RowsSizing>;
        aria_hidden: p.Property<boolean>;
    }
}

export interface ExtendedColumn extends ExtendedColumn.Attrs { }

export class ExtendedColumn extends Box {
    properties: ExtendedColumn.Props
    __view_type__: ExtendedColumnView

    constructor(attrs?: Partial<ExtendedColumn.Attrs>) {
        super(attrs)
    }

    static init_ExtendedColumn(): void {
        this.prototype.default_view = ExtendedColumnView

        this.define<ExtendedColumn.Props>(({ Any }) => ({
            rows: [Any /*TODO*/, "auto"],
            aria_hidden: [p.Boolean, false],
        }))
    }
}
