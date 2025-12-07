import {InputWidget, InputWidgetView} from "models/widgets/input_widget";
import {select, option} from "core/dom";
//import { isString } from "core/util/types";
// import { bk_input } from "styles/widgets/inputs";
import * as p from "core/properties";

declare function jQuery(...args: any[]): any;

export class BootstrapSelectView extends InputWidgetView {
    model: BootstrapSelect;

    protected select_el: HTMLSelectElement;

    connect_signals(): void {
        super.connect_signals();
        this.connect(this.model.properties.value.change, () =>
            this.render_selection()
        );
    }

    render(): void {
        super.render();
        const options = this.model.options.map((opts) => {
            let _label, _d, value, title;
            let data: any = {};

            [_label, _d] = opts;
            [value, data.subtext] = _d;

            title = _label;
            if (data.subtext) title = data.subtext;

            return option({value, data, title}, _label);
        });

        this.select_el = select(
            {
                multiple: true,
                title: this.model.alt_title,
                disabled: false,
            },
            options
        );

        this.group_el.appendChild(this.select_el);
        this.render_selection();

        let select_opts: any = {};

        select_opts.title = this.model.alt_title;
        select_opts.actionsBox = this.model.actions_box;
        select_opts.liveSearch = this.model.live_search;
        //select_opts.showSubtext = this.model.show_subtext;

        if (this.model.count_selected_text)
            select_opts.countSelectedText = this.model.count_selected_text;

        if (this.model.none_selected_text)
            select_opts.noneSelectedText = this.model.none_selected_text;

        if (this.model.selected_text_format)
            select_opts.selectedTextFormat = this.model.selected_text_format;

        if (this.model.none_results_text)
            select_opts.noneResultsText = this.model.none_results_text;
        jQuery(this.select_el).selectpicker(select_opts);

        if (this.model.select_all_at_start)
            jQuery(this.select_el).selectpicker("selectAll");

        setTimeout(() => {
            jQuery('ul.dropdown-menu').addClass('dropdown__list');
            jQuery('ul.dropdown-menu').children('li').addClass('dropdown-item');
            jQuery('select.bk').on('show.bs.select', () => {
                jQuery('ul.dropdown-menu').children('li').addClass('dropdown-item');
            });
            jQuery('button.dropdown-toggle').removeClass('btn-light');
        })

        this.select_el.addEventListener("change", () => this.change_input());
    }

    render_selection(): void {
        const ids = new Set(
            this.model.value.map((v) => {
                return v[0].toString();
            })
        );

        for (const el of Array.from(this.el.querySelectorAll("option"))) {
            el.selected = ids.has(el.value);
        }
    }

    change_input(): void {
        const values = [];
        for (const el of this.el.querySelectorAll("option")) {
            if (el.selected) {
                const opts = this.model.options.filter(
                    (item) => item[1][0] == el.value
                );
                for (let opt of opts) {
                    values.push(opt[1]);
                }
                jQuery(el).parent().addClass('active')
            }
        }
        this.model.value = values;
        super.change_input();
    }
}

export namespace BootstrapSelect {
    export type Attrs = p.AttrsOf<Props>;
    export type Props = InputWidget.Props & {
        alt_title: p.Property<string>;
        value: p.Property<[string | number, string][]>;
        options: p.Property<[string, [number | string, string]][]>;
        actions_box: p.Property<boolean>;
        live_search: p.Property<boolean>;
        // show_subtext: p.Property<boolean>;
        select_all_at_start: p.Property<boolean>;
        count_selected_text: p.Property<string>;
        none_selected_text: p.Property<string>;
        selected_text_format: p.Property<string>;
        none_results_text: p.Property<string>;
    };
}

export interface BootstrapSelect extends BootstrapSelect.Attrs {
}

export class BootstrapSelect extends InputWidget {
    properties: BootstrapSelect.Props;
    __view_type__: BootstrapSelectView;

    constructor(attrs?: Partial<BootstrapSelect.Attrs>) {
        super(attrs);
    }

    static init_BootstrapSelect(): void {
        this.prototype.default_view = BootstrapSelectView;

        this.define<BootstrapSelect.Props>({
            alt_title: [p.String, ""],
            value: [p.Array, []],
            options: [p.Array, []],
            actions_box: [p.Boolean, false],
            live_search: [p.Boolean, false],
            // show_subtext: [p.Boolean, false],
            select_all_at_start: [p.Boolean, false],
            none_selected_text: [p.String, ""],
            count_selected_text: [p.String, ""],
            selected_text_format: [p.String, ""],
            none_results_text: [p.String, ""],
        });
    }
}
