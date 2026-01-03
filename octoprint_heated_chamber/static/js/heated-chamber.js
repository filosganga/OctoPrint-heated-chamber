/*
 * View model for OctoPrint-Heatedchamber
 *
 * Author: Filippo De Luca
 * License: AGPLv3
 */
$(function() {
    function HeatedChamberViewModel(parameters) {
        var self = this;
        self.settingsViewModel = parameters[0];
        self.ds18b20Devices = ko.observableArray([]);
        self.isLoadingDevices = ko.observable(false);

        self.settings = null;

        self.onBeforeBinding = function() {
            self.settings = self.settingsViewModel.settings.plugins.heated_chamber;
        };

        self.onSettingsShown = function() {
            self.refreshDs18b20Devices();
        };

        self.refreshDs18b20Devices = function() {
            self.isLoadingDevices(true);
            OctoPrint.simpleApiGet("heated_chamber", { action: "listDs18b20Devices" })
                .done(function(response) {
                    self.ds18b20Devices(response);
                })
                .fail(function() {
                    self.ds18b20Devices([]);
                })
                .always(function() {
                    self.isLoadingDevices(false);
                });
        };
    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: HeatedChamberViewModel,
        dependencies: ["settingsViewModel"],
        elements: ["#settings_plugin_heated_chamber"]
    });
});
