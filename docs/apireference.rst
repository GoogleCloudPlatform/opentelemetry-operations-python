API Reference
=============

..
   The above .. prevents the autosummary table from rendering in the
   document, but still causes the recursive generation of autodoc stub files.

   .. autosummary::
      :toctree: _autosummary
      :caption: API Reference
      :template: custom-module-template.rst
      :recursive:

      opentelemetry.exporter
      opentelemetry.propagators.cloud_trace_propagator
      opentelemetry.resourcedetector


.. toctree::
   :maxdepth: 5
   :caption: API Reference
   :name: apireference

   _autosummary/opentelemetry.exporter
   _autosummary/opentelemetry.propagators.cloud_trace_propagator
   _autosummary/opentelemetry.resourcedetector
