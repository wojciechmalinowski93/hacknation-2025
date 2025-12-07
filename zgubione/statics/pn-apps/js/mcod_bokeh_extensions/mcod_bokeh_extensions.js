/*!
 * Copyright (c) 2012 - 2021, Anaconda, Inc., and Bokeh Contributors
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without modification,
 * are permitted provided that the following conditions are met:
 *
 * Redistributions of source code must retain the above copyright notice,
 * this list of conditions and the following disclaimer.
 *
 * Redistributions in binary form must reproduce the above copyright notice,
 * this list of conditions and the following disclaimer in the documentation
 * and/or other materials provided with the distribution.
 *
 * Neither the name of Anaconda nor the names of any contributors
 * may be used to endorse or promote products derived from this software
 * without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
 * THE POSSIBILITY OF SUCH DAMAGE.
 */
(function(root, factory) {
  factory(root["Bokeh"], undefined);
})(this, function(Bokeh, version) {
  let define;
  return (function(modules, entry, aliases, externals) {
    const bokeh = typeof Bokeh !== "undefined" && (version != null ? Bokeh[version] : Bokeh);
    if (bokeh != null) {
      return bokeh.register_plugin(modules, entry, aliases);
    } else {
      throw new Error("Cannot find Bokeh " + version + ". You have to load it prior to loading plugins.");
    }
  })
({
"07f0dba833": /* index.js */ function _(require, module, exports, __esModule, __esExport) {
    __esModule();
    const bootstrap_select_1 = require("755200687e") /* ./widgets/bootstrap_select */;
    const extendedradiobuttongroup_1 = require("086f1b620e") /* ./widgets/extendedradiobuttongroup */;
    const localized_hover_tool_1 = require("e5fbf9373b") /* ./tools/localized_hover_tool */;
    const localized_pan_tool_1 = require("1fe940bc2d") /* ./tools/localized_pan_tool */;
    const localized_save_tool_1 = require("4048676921") /* ./tools/localized_save_tool */;
    const localized_wheel_zoom_tool_1 = require("2c6dec8f7c") /* ./tools/localized_wheel_zoom_tool */;
    const localized_reset_tool_1 = require("563a659345") /* ./tools/localized_reset_tool */;
    const extendedcolumn_1 = require("91d9730b00") /* ./layouts/extendedcolumn */;
    const base_1 = require("@bokehjs/base");
    (0, base_1.register_models)({ BootstrapSelect: bootstrap_select_1.BootstrapSelect, LocalizedHoverTool: localized_hover_tool_1.LocalizedHoverTool, LocalizedPanTool: localized_pan_tool_1.LocalizedPanTool,
        LocalizedSaveTool: localized_save_tool_1.LocalizedSaveTool, LocalizedWheelZoomTool: localized_wheel_zoom_tool_1.LocalizedWheelZoomTool, LocalizedResetTool: localized_reset_tool_1.LocalizedResetTool, ExtendedColumn: extendedcolumn_1.ExtendedColumn, ExtendedRadioButtonGroup: extendedradiobuttongroup_1.ExtendedRadioButtonGroup });
},
"755200687e": /* widgets/bootstrap_select.js */ function _(require, module, exports, __esModule, __esExport) {
    __esModule();
    const tslib_1 = require("tslib");
    var _a;
    const input_widget_1 = require("@bokehjs/models/widgets/input_widget");
    const dom_1 = require("@bokehjs/core/dom");
    //import { isString } from "core/util/types";
    // import { bk_input } from "styles/widgets/inputs";
    const p = (0, tslib_1.__importStar)(require("@bokehjs/core/properties"));
    class BootstrapSelectView extends input_widget_1.InputWidgetView {
        connect_signals() {
            super.connect_signals();
            this.connect(this.model.properties.value.change, () => this.render_selection());
        }
        render() {
            super.render();
            const options = this.model.options.map((opts) => {
                let _label, _d, value, title;
                let data = {};
                [_label, _d] = opts;
                [value, data.subtext] = _d;
                title = _label;
                if (data.subtext)
                    title = data.subtext;
                return (0, dom_1.option)({ value, data, title }, _label);
            });
            this.select_el = (0, dom_1.select)({
                multiple: true,
                title: this.model.alt_title,
                disabled: false,
            }, options);
            this.group_el.appendChild(this.select_el);
            this.render_selection();
            let select_opts = {};
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
            });
            this.select_el.addEventListener("change", () => this.change_input());
        }
        render_selection() {
            const ids = new Set(this.model.value.map((v) => {
                return v[0].toString();
            }));
            for (const el of Array.from(this.el.querySelectorAll("option"))) {
                el.selected = ids.has(el.value);
            }
        }
        change_input() {
            const values = [];
            for (const el of this.el.querySelectorAll("option")) {
                if (el.selected) {
                    const opts = this.model.options.filter((item) => item[1][0] == el.value);
                    for (let opt of opts) {
                        values.push(opt[1]);
                    }
                    jQuery(el).parent().addClass('active');
                }
            }
            this.model.value = values;
            super.change_input();
        }
    }
    exports.BootstrapSelectView = BootstrapSelectView;
    BootstrapSelectView.__name__ = "BootstrapSelectView";
    class BootstrapSelect extends input_widget_1.InputWidget {
        constructor(attrs) {
            super(attrs);
        }
    }
    exports.BootstrapSelect = BootstrapSelect;
    _a = BootstrapSelect;
    BootstrapSelect.__name__ = "BootstrapSelect";
    BootstrapSelect.__module__ = "mcod.pn_apps.bokeh.widgets";
    (() => {
        _a.prototype.default_view = BootstrapSelectView;
        _a.define({
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
    })();
},
"086f1b620e": /* widgets/extendedradiobuttongroup.js */ function _(require, module, exports, __esModule, __esExport) {
    __esModule();
    const tslib_1 = require("tslib");
    var _a;
    const button_group_1 = require("@bokehjs/models/widgets/button_group");
    const dom_1 = require("@bokehjs/core/dom");
    const buttons = (0, tslib_1.__importStar)(require("@bokehjs/styles/buttons.css"));
    class ExtendedRadioButtonGroupView extends button_group_1.ButtonGroupView {
        render() {
            super.render();
            this._buttons.forEach((button) => {
                button.setAttribute('tabindex', "0");
            });
        }
        change_active(i) {
            if (this.model.active !== i) {
                this.model.active = i;
            }
        }
        _update_active() {
            const { active } = this.model;
            this._buttons.forEach((button, i) => {
                (0, dom_1.classes)(button).toggle(buttons.active, active === i);
            });
        }
    }
    exports.ExtendedRadioButtonGroupView = ExtendedRadioButtonGroupView;
    ExtendedRadioButtonGroupView.__name__ = "ExtendedRadioButtonGroupView";
    class ExtendedRadioButtonGroup extends button_group_1.ButtonGroup {
        constructor(attrs) {
            super(attrs);
        }
    }
    exports.ExtendedRadioButtonGroup = ExtendedRadioButtonGroup;
    _a = ExtendedRadioButtonGroup;
    ExtendedRadioButtonGroup.__name__ = "ExtendedRadioButtonGroup";
    ExtendedRadioButtonGroup.__module__ = "mcod.pn_apps.bokeh.widgets";
    (() => {
        _a.prototype.default_view = ExtendedRadioButtonGroupView;
        _a.define(({ Int, Nullable }) => ({
            active: [Nullable(Int), null],
        }));
    })();
},
"e5fbf9373b": /* tools/localized_hover_tool.js */ function _(require, module, exports, __esModule, __esExport) {
    __esModule();
    const tslib_1 = require("tslib");
    var _a;
    const hover_tool_1 = require("@bokehjs/models/tools/inspectors/hover_tool");
    const p = (0, tslib_1.__importStar)(require("@bokehjs/core/properties"));
    class LocalizedHoverTool extends hover_tool_1.HoverTool {
        constructor(attrs) {
            super(attrs);
            this.tool_name = this.localized_tool_name;
            this.icon = "bk-tool-icon-custom-hover";
        }
    }
    exports.LocalizedHoverTool = LocalizedHoverTool;
    _a = LocalizedHoverTool;
    LocalizedHoverTool.__name__ = "LocalizedHoverTool";
    LocalizedHoverTool.__module__ = "mcod.pn_apps.bokeh.tools.base";
    (() => {
        _a.prototype.default_view = hover_tool_1.HoverToolView;
        _a.define({
            localized_tool_name: [p.String, ""],
        });
    })();
},
"1fe940bc2d": /* tools/localized_pan_tool.js */ function _(require, module, exports, __esModule, __esExport) {
    __esModule();
    const tslib_1 = require("tslib");
    var _a;
    const pan_tool_1 = require("@bokehjs/models/tools/gestures/pan_tool");
    const p = (0, tslib_1.__importStar)(require("@bokehjs/core/properties"));
    class LocalizedPanTool extends pan_tool_1.PanTool {
        constructor(attrs) {
            super(attrs);
            this.tool_name = this.localized_tool_name;
        }
        get computed_icon() {
            switch (this.dimensions) {
                case "both": return this.icon;
                case "width": return "bk-tool-icon-custom-pan";
                case "height": return this.icon;
            }
        }
        get tooltip() {
            return this.tool_name;
        }
    }
    exports.LocalizedPanTool = LocalizedPanTool;
    _a = LocalizedPanTool;
    LocalizedPanTool.__name__ = "LocalizedPanTool";
    LocalizedPanTool.__module__ = "mcod.pn_apps.bokeh.tools.base";
    (() => {
        _a.prototype.default_view = pan_tool_1.PanToolView;
        _a.define({
            localized_tool_name: [p.String, ""],
        });
    })();
},
"4048676921": /* tools/localized_save_tool.js */ function _(require, module, exports, __esModule, __esExport) {
    __esModule();
    const tslib_1 = require("tslib");
    var _a;
    const save_tool_1 = require("@bokehjs/models/tools/actions/save_tool");
    const p = (0, tslib_1.__importStar)(require("@bokehjs/core/properties"));
    class LocalizedSaveTool extends save_tool_1.SaveTool {
        constructor(attrs) {
            super(attrs);
            this.tool_name = this.localized_tool_name;
            this.icon = "bk-tool-icon-custom-save";
        }
    }
    exports.LocalizedSaveTool = LocalizedSaveTool;
    _a = LocalizedSaveTool;
    LocalizedSaveTool.__name__ = "LocalizedSaveTool";
    LocalizedSaveTool.__module__ = "mcod.pn_apps.bokeh.tools.base";
    (() => {
        _a.prototype.default_view = save_tool_1.SaveToolView;
        _a.define({
            localized_tool_name: [p.String],
        });
    })();
},
"2c6dec8f7c": /* tools/localized_wheel_zoom_tool.js */ function _(require, module, exports, __esModule, __esExport) {
    __esModule();
    const tslib_1 = require("tslib");
    var _a;
    const wheel_zoom_tool_1 = require("@bokehjs/models/tools/gestures/wheel_zoom_tool");
    const p = (0, tslib_1.__importStar)(require("@bokehjs/core/properties"));
    class LocalizedWheelZoomTool extends wheel_zoom_tool_1.WheelZoomTool {
        constructor(attrs) {
            super(attrs);
            this.tool_name = this.localized_tool_name;
            this.icon = "bk-tool-icon-custom-wheel-zoom";
        }
        get tooltip() {
            return this.tool_name;
        }
    }
    exports.LocalizedWheelZoomTool = LocalizedWheelZoomTool;
    _a = LocalizedWheelZoomTool;
    LocalizedWheelZoomTool.__name__ = "LocalizedWheelZoomTool";
    LocalizedWheelZoomTool.__module__ = "mcod.pn_apps.bokeh.tools.base";
    (() => {
        _a.prototype.default_view = wheel_zoom_tool_1.WheelZoomToolView;
        _a.define({
            localized_tool_name: [p.String],
        });
    })();
},
"563a659345": /* tools/localized_reset_tool.js */ function _(require, module, exports, __esModule, __esExport) {
    __esModule();
    const tslib_1 = require("tslib");
    var _a;
    const reset_tool_1 = require("@bokehjs/models/tools/actions/reset_tool");
    const p = (0, tslib_1.__importStar)(require("@bokehjs/core/properties"));
    class LocalizedResetTool extends reset_tool_1.ResetTool {
        constructor(attrs) {
            super(attrs);
            this.tool_name = this.localized_tool_name;
            this.icon = "bk-tool-icon-custom-reset";
        }
    }
    exports.LocalizedResetTool = LocalizedResetTool;
    _a = LocalizedResetTool;
    LocalizedResetTool.__name__ = "LocalizedResetTool";
    LocalizedResetTool.__module__ = "mcod.pn_apps.bokeh.tools.base";
    (() => {
        _a.prototype.default_view = reset_tool_1.ResetToolView;
        _a.define({
            localized_tool_name: [p.String],
        });
    })();
},
"91d9730b00": /* layouts/extendedcolumn.js */ function _(require, module, exports, __esModule, __esExport) {
    __esModule();
    const tslib_1 = require("tslib");
    var _a;
    const box_1 = require("@bokehjs/models/layouts/box");
    const grid_1 = require("@bokehjs/core/layout/grid");
    const p = (0, tslib_1.__importStar)(require("@bokehjs/core/properties"));
    class ExtendedColumnView extends box_1.BoxView {
        render() {
            super.render();
            this.el.setAttribute('aria-hidden', this.model.aria_hidden.toString());
        }
        _update_layout() {
            const items = this.child_views.map((child) => child.layout);
            this.layout = new grid_1.Column(items);
            this.layout.rows = this.model.rows;
            this.layout.spacing = [this.model.spacing, 0];
            this.layout.set_sizing(this.box_sizing());
        }
    }
    exports.ExtendedColumnView = ExtendedColumnView;
    ExtendedColumnView.__name__ = "ExtendedColumnView";
    class ExtendedColumn extends box_1.Box {
        constructor(attrs) {
            super(attrs);
        }
    }
    exports.ExtendedColumn = ExtendedColumn;
    _a = ExtendedColumn;
    ExtendedColumn.__name__ = "ExtendedColumn";
    ExtendedColumn.__module__ = "mcod.pn_apps.bokeh.layouts";
    (() => {
        _a.prototype.default_view = ExtendedColumnView;
        _a.define(({ Any }) => ({
            rows: [Any /*TODO*/, "auto"],
            aria_hidden: [p.Boolean, false],
        }));
    })();
},
}, "07f0dba833", {"index":"07f0dba833","widgets/bootstrap_select":"755200687e","widgets/extendedradiobuttongroup":"086f1b620e","tools/localized_hover_tool":"e5fbf9373b","tools/localized_pan_tool":"1fe940bc2d","tools/localized_save_tool":"4048676921","tools/localized_wheel_zoom_tool":"2c6dec8f7c","tools/localized_reset_tool":"563a659345","layouts/extendedcolumn":"91d9730b00"}, {});});
//# sourceMappingURL=bokeh_2.4.2_ext.js.map
